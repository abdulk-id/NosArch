import argparse
import os
import sys
import traceback
from collections.abc import Callable

import nosarch.engine.aur
import nosarch.engine.changes
import nosarch.engine.command
import nosarch.engine.fs
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.session
import nosarch.engine.setup
import nosarch.engine.state
import nosarch.engine.steps
import nosarch.engine.steps.files
import nosarch.engine.steps.users


def _arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="python -m nosarch",
        description="Deploys the NosArch configuration. Re-runs itself with sudo unless it is a dry run.",
    )
    parser.add_argument("--dry-run", action="store_true", help="show what would change without applying changes")
    parser.add_argument("--only", nargs="+", default=[], metavar="STEP", help="run only these steps")
    parser.add_argument("--skip", nargs="+", default=[], metavar="STEP", help="skip these steps")
    parser.add_argument("--no-hooks", action="store_true", help="run no module hooks")
    parser.add_argument("--aur-upgrade-devel", action="store_true", help="rebuild VCS packages such as -git ones")
    parser.add_argument("--debug", action="store_true", help="print every command that runs")
    return parser.parse_args()


def _rerun_as_root() -> None:
    nosarch.engine.output.print_info("Applying needs root, re-running with sudo.")
    # sudo clears PYTHONPATH. The file puts its parent on the path, so the restart does not depend on it.
    main_file: str = os.path.join(os.path.dirname(os.path.abspath(nosarch.__file__)), "__main__.py")
    os.execvp("sudo", ["sudo", sys.executable, "-B", main_file, *sys.argv[1:]])


def _selected_steps(setup: nosarch.engine.setup.Setup, args: argparse.Namespace) -> list[str]:
    for name in [*args.only, *args.skip, *setup.steps]:
        if name not in nosarch.engine.steps.STEPS:
            raise ValueError(f"Unknown step '{name}'. Steps are: {', '.join(nosarch.engine.steps.STEPS)}.")

    selected: list[str] = [step for step in setup.steps if not args.only or step in args.only]
    return [step for step in selected if step not in args.skip]


def _diff_declarations(ctx: nosarch.engine.setup.Context, kinds: tuple[str, ...]) -> None:
    for module in ctx.setup.modules:
        previous: dict[str, list[str]] = ctx.state.declared.get(module.name, {})

        for kind in kinds:
            before: set[str] = set(previous.get(kind, []))
            after: set[str] = nosarch.engine.module.identities(kind, ctx.declarations[module.name][kind])
            changes: nosarch.engine.changes.Changes = ctx.changes_for(module.name)
            changes.added_pkgs[kind] |= after - before
            changes.removed_pkgs[kind] |= before - after
            if not ctx.dry_run:
                ctx.state.declared.setdefault(module.name, {})[kind] = sorted(after)


def _unseen_changes(
    ctx: nosarch.engine.setup.Context, carried: dict[str, nosarch.engine.changes.Changes], module: str
) -> nosarch.engine.changes.Changes:
    merged: nosarch.engine.changes.Changes = nosarch.engine.changes.Changes()
    merged.merge(carried.get(module, nosarch.engine.changes.Changes()))
    merged.merge(ctx.changes.get(module, nosarch.engine.changes.Changes()))
    return merged


def _run_step(ctx: nosarch.engine.setup.Context, step: str, carried: dict[str, nosarch.engine.changes.Changes]) -> None:
    nosarch.engine.steps.STEPS[step](ctx)
    _diff_declarations(ctx, nosarch.engine.steps.KINDS.get(step, ()))
    if ctx.dry_run:
        return

    for module in ctx.setup.modules:
        unseen: nosarch.engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
        if unseen:
            ctx.state.pending[module.name] = unseen.to_json()
        else:
            ctx.state.pending.pop(module.name, None)
    ctx.state.save()


def run(setup: nosarch.engine.setup.Setup, args: argparse.Namespace) -> None:
    dry: bool = args.dry_run
    hooks: bool = not args.no_hooks and not dry
    setup.aur.upgrade_devel = args.aur_upgrade_devel

    state: nosarch.engine.state.State = nosarch.engine.state.load() or nosarch.engine.state.State()
    ctx: nosarch.engine.setup.Context = nosarch.engine.setup.Context(setup=setup, state=state, dry_run=dry)
    steps: list[str] = _selected_steps(setup, args)

    enabled: set[str] = {module.name for module in setup.modules}
    known: dict[str, nosarch.engine.module.Module] = {module.name: module for module in setup.disabled_modules}
    new: list[nosarch.engine.module.Module] = [
        module for module in setup.modules if module.name not in state.enabled_modules
    ]
    disabled: list[str] = [name for name in state.enabled_modules if name not in enabled]
    carried: dict[str, nosarch.engine.changes.Changes] = {
        module.name: state.pending_changes(module.name) for module in setup.modules
    }

    for module in setup.modules:
        ctx.declarations[module.name] = nosarch.engine.module.declarations(module)

    if "users" in steps:
        _run_step(ctx, "users", carried)

    if hooks:
        nosarch.engine.output.print_summary("Running before_update hooks.")
        for module in setup.modules:
            module.before_update()

        for name in disabled:
            nosarch.engine.output.print_summary(f"Running on_disable for {name}.")
            if name in known:
                known[name].on_disable()
            else:
                nosarch.engine.output.print_warning(f"Module {name} no longer exists, so its on_disable cannot run.")
            state.enabled_modules.remove(name)
            state.declared.pop(name, None)
            state.pending.pop(name, None)
            state.save()

    for step in steps:
        if step != "users":
            _run_step(ctx, step, carried)

    if "users" in steps and not dry:
        nosarch.engine.steps.users.finish(ctx)

    if dry:
        nosarch.engine.output.print_list("Modules that would be enabled:", [module.name for module in new])
        nosarch.engine.output.print_list("Modules that would be disabled, running on_disable:", disabled)
        for module in setup.modules:
            unseen: nosarch.engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
            if unseen:
                nosarch.engine.output.print_list(
                    f"on_change of {module.name} would see:", unseen.summary(), one_per_line=True
                )
        nosarch.engine.output.print_summary("Dry run finished. Nothing was changed.")
        return

    if hooks:
        for module in new:
            nosarch.engine.output.print_summary(f"Running on_enable for {module.name}.")
            module.on_enable()
            state.enabled_modules.append(module.name)
            state.save()

        for module in setup.modules:
            unseen: nosarch.engine.changes.Changes = state.pending_changes(module.name)
            if not unseen:
                continue
            nosarch.engine.output.print_summary(f"Running on_change for {module.name}.")
            nosarch.engine.output.print_debug(f"It sees: {'; '.join(unseen.summary())}")
            module.on_change(unseen)
            state.pending.pop(module.name, None)
            state.save()

        nosarch.engine.output.print_summary("Running after_update hooks.")
        for module in setup.modules:
            module.after_update()

    state.save()
    nosarch.engine.output.print_summary("Done.")
    nosarch.engine.session.offer(prompt=sys.stdin.isatty())


def main(build_setup: Callable[[], nosarch.engine.setup.Setup]) -> None:
    args: argparse.Namespace = _arguments()
    nosarch.engine.output.debug_output = args.debug

    if not args.dry_run and not nosarch.engine.command.is_root():
        _rerun_as_root()

    try:
        run(build_setup(), args)
    except KeyboardInterrupt:
        nosarch.engine.output.print_error("Interrupted.")

        sys.exit(130)
    except nosarch.engine.command.CommandFailedError as error:
        nosarch.engine.output.print_error(str(error))
        if error.output:
            print(error.output, file=sys.stderr)

        sys.exit(1)
    except ValueError as error:
        nosarch.engine.output.print_error("ValueError raised from the source.")
        nosarch.engine.output.print_error(str(error))
        if args.debug:
            traceback.print_exc()

        sys.exit(1)
    except (
        nosarch.engine.aur.AurError,
        nosarch.engine.command.AccountNotFoundError,
        nosarch.engine.fs.InstallError,
        nosarch.engine.steps.files.DuplicateTargetError,
        PermissionError,
        RuntimeError,
    ) as error:
        nosarch.engine.output.print_error(str(error))
        if args.debug:
            traceback.print_exc()

        sys.exit(1)
