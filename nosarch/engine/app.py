import argparse
import os
import sys
import traceback
from collections.abc import Callable

import engine.aur
import engine.changes
import engine.command
import engine.fs
import engine.module
import engine.output
import engine.session
import engine.setup
import engine.state
import engine.steps
import engine.steps.files
import engine.steps.users


def _arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="nosarch/apply.py",
        description="Deploys the NosArch configuration. Re-runs itself with sudo unless it is a dry run.",
    )
    parser.add_argument("--dry-run", action="store_true", help="show what would change, without root or changes")
    parser.add_argument("--only", nargs="+", default=[], metavar="STEP", help="run only these steps")
    parser.add_argument("--skip", nargs="+", default=[], metavar="STEP", help="skip these steps")
    parser.add_argument("--no-hooks", action="store_true", help="run no module hooks")
    parser.add_argument("--aur-upgrade-devel", action="store_true", help="rebuild VCS packages such as -git ones")
    parser.add_argument("--debug", action="store_true", help="print every command that runs")
    return parser.parse_args()


def _reexec_as_root() -> None:
    engine.output.print_info("Applying needs root, re-running with sudo.")
    script: str = os.path.abspath(sys.argv[0])
    os.execvp("sudo", ["sudo", sys.executable, "-B", script, *sys.argv[1:]])


def _selected_steps(setup: engine.setup.Setup, args: argparse.Namespace) -> list[str]:
    for name in [*args.only, *args.skip, *setup.steps]:
        if name not in engine.steps.STEPS:
            raise ValueError(f"Unknown step '{name}'. Steps are: {', '.join(engine.steps.STEPS)}.")

    selected: list[str] = [step for step in setup.steps if not args.only or step in args.only]
    return [step for step in selected if step not in args.skip]


def _diff_declarations(ctx: engine.setup.Context, kinds: tuple[str, ...]) -> None:
    for module in ctx.setup.modules:
        previous: dict[str, list[str]] = ctx.state.declared.get(module.name, {})
        for kind in kinds:
            before: set[str] = set(previous.get(kind, []))
            after: set[str] = engine.module.identities(kind, ctx.declarations[module.name][kind])
            changes: engine.changes.Changes = ctx.changes_for(module.name)
            changes.added_pkgs[kind] |= after - before
            changes.removed_pkgs[kind] |= before - after
            if not ctx.dry_run:
                ctx.state.declared.setdefault(module.name, {})[kind] = sorted(after)


def _unseen_changes(
    ctx: engine.setup.Context, carried: dict[str, engine.changes.Changes], module: str
) -> engine.changes.Changes:
    merged: engine.changes.Changes = engine.changes.Changes()
    merged.merge(carried.get(module, engine.changes.Changes()))
    merged.merge(ctx.changes.get(module, engine.changes.Changes()))
    return merged


def _run_step(ctx: engine.setup.Context, step: str, carried: dict[str, engine.changes.Changes]) -> None:
    engine.steps.STEPS[step](ctx)
    _diff_declarations(ctx, engine.steps.KINDS.get(step, ()))
    if ctx.dry_run:
        return

    for module in ctx.setup.modules:
        unseen: engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
        if unseen:
            ctx.state.pending[module.name] = unseen.to_json()
        else:
            ctx.state.pending.pop(module.name, None)
    ctx.state.save()


def run(setup: engine.setup.Setup, args: argparse.Namespace) -> None:
    dry: bool = args.dry_run
    hooks: bool = not args.no_hooks and not dry
    setup.aur.upgrade_devel = args.aur_upgrade_devel

    state: engine.state.State = engine.state.load() or engine.state.State()
    ctx: engine.setup.Context = engine.setup.Context(setup=setup, state=state, dry_run=dry)
    steps: list[str] = _selected_steps(setup, args)

    enabled: set[str] = {module.name for module in setup.modules}
    known: dict[str, engine.module.Module] = {module.name: module for module in setup.disabled_modules}
    new: list[engine.module.Module] = [module for module in setup.modules if module.name not in state.enabled_modules]
    disabled: list[str] = [name for name in state.enabled_modules if name not in enabled]
    carried: dict[str, engine.changes.Changes] = {
        module.name: state.pending_changes(module.name) for module in setup.modules
    }

    for module in setup.modules:
        ctx.declarations[module.name] = engine.module.declarations(module)

    if "users" in steps:
        _run_step(ctx, "users", carried)

    if hooks:
        engine.output.print_summary("Running before_update hooks.")
        for module in setup.modules:
            module.before_update()

        for name in disabled:
            engine.output.print_summary(f"Running on_disable for {name}.")
            if name in known:
                known[name].on_disable()
            else:
                engine.output.print_warning(f"Module {name} no longer exists, so its on_disable cannot run.")
            state.enabled_modules.remove(name)
            state.declared.pop(name, None)
            state.pending.pop(name, None)
            state.save()

    for step in steps:
        if step != "users":
            _run_step(ctx, step, carried)

    if "users" in steps and not dry:
        engine.steps.users.finish(ctx)

    if dry:
        engine.output.print_list("Modules that would be enabled:", [module.name for module in new])
        engine.output.print_list("Modules that would be disabled, running on_disable:", disabled)
        for module in setup.modules:
            unseen: engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
            if unseen:
                engine.output.print_list(f"on_change of {module.name} would see:", unseen.summary(), one_per_line=True)
        engine.output.print_summary("Dry run finished. Nothing was changed.")
        return

    if hooks:
        for module in new:
            engine.output.print_summary(f"Running on_enable for {module.name}.")
            module.on_enable()
            state.enabled_modules.append(module.name)
            state.save()

        for module in setup.modules:
            unseen: engine.changes.Changes = state.pending_changes(module.name)
            if not unseen:
                continue
            engine.output.print_summary(f"Running on_change for {module.name}.")
            engine.output.print_debug(f"It sees: {'; '.join(unseen.summary())}")
            module.on_change(unseen)
            state.pending.pop(module.name, None)
            state.save()

        engine.output.print_summary("Running after_update hooks.")
        for module in setup.modules:
            module.after_update()

    state.save()
    engine.output.print_summary("Done.")
    engine.session.offer(prompt=sys.stdin.isatty())


def main(build_setup: Callable[[], engine.setup.Setup]) -> None:
    args: argparse.Namespace = _arguments()
    engine.output.debug_output = args.debug

    if not args.dry_run and not engine.command.is_root():
        _reexec_as_root()

    try:
        run(build_setup(), args)
    except KeyboardInterrupt:
        engine.output.print_error("Interrupted.")
        sys.exit(130)
    except engine.command.CommandFailedError as error:
        engine.output.print_error(str(error))
        if error.output:
            print(error.output, file=sys.stderr)
        sys.exit(1)
    except ValueError as error:
        engine.output.print_error("ValueError raised from the source.")
        engine.output.print_error(str(error))
        if args.debug:
            traceback.print_exc()
        sys.exit(1)
    except (
        engine.aur.AurError,
        engine.command.AccountNotFoundError,
        engine.fs.InstallError,
        engine.steps.files.DuplicateTargetError,
        PermissionError,
        RuntimeError,
    ) as error:
        engine.output.print_error(str(error))
        if args.debug:
            traceback.print_exc()
        sys.exit(1)
