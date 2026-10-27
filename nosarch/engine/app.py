"""The command line, and the order a run goes in."""

import argparse
import os
import sys
import traceback
from collections.abc import Callable

import engine.aur
import engine.changes
import engine.command
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
    parser.add_argument("--import-decman", action="store_true", help="only import decman's state, then exit")
    parser.add_argument("--debug", action="store_true", help="print every command that runs")
    return parser.parse_args()


def _reexec_as_root() -> None:
    """A real run needs root. Asking for it here means nobody has to remember `sudo`, and a dry run never needs it."""

    engine.output.print_info("Applying needs root, re-running with sudo.")
    script: str = os.path.abspath(sys.argv[0])
    os.execvp("sudo", ["sudo", sys.executable, "-B", script, *sys.argv[1:]])


def _load_state(dry_run: bool) -> engine.state.State:
    state: engine.state.State | None = engine.state.load()
    if state is not None:
        return state

    if not engine.state.decman_store_exists():
        return engine.state.State()

    if engine.command.is_root():
        state = engine.state.import_decman_store()
        if not dry_run:
            state.save()
        return state

    engine.output.print_warning(
        "There is no NosArch state yet, and decman's is only readable by root. Run `nosarch/apply.py --import-decman` "
        "once. Until then a dry run sees every module as new."
    )
    return engine.state.State()


def _selected_steps(setup: engine.setup.Setup, args: argparse.Namespace) -> list[str]:
    for name in [*args.only, *args.skip, *setup.steps]:
        if name not in engine.steps.STEPS:
            raise ValueError(f"Unknown step '{name}'. Steps are: {', '.join(engine.steps.STEPS)}.")

    selected: list[str] = [step for step in setup.steps if not args.only or step in args.only]
    return [step for step in selected if step not in args.skip]


def _diff_declarations(ctx: engine.setup.Context, kinds: tuple[str, ...]) -> None:
    """Records what each module added or removed, for the kinds a step that just ran acts on."""

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
    """What `module`'s on_change has not seen yet: what earlier runs left, and what this run changed."""

    merged: engine.changes.Changes = engine.changes.Changes()
    merged.merge(carried.get(module, engine.changes.Changes()))
    merged.merge(ctx.changes.get(module, engine.changes.Changes()))
    return merged


def _save_unseen(ctx: engine.setup.Context, carried: dict[str, engine.changes.Changes]) -> None:
    """
    Saves the changes no hook has seen yet, after every step.

    A change is only noticed on the run that makes it: the next run finds the file already in place. Saving it before
    the hooks run means a run that stops partway still hands it to the hook on the next run.
    """

    for module in ctx.setup.modules:
        unseen: engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
        if unseen:
            ctx.state.pending[module.name] = unseen.to_json()
        else:
            ctx.state.pending.pop(module.name, None)
    ctx.state.save()


def _report_dry_run(
    ctx: engine.setup.Context,
    carried: dict[str, engine.changes.Changes],
    new: list[engine.module.Module],
    disabled: list[str],
) -> None:
    engine.output.print_list("Modules that would be enabled:", [module.name for module in new])
    engine.output.print_list("Modules that would be disabled, running on_disable:", disabled)

    for module in ctx.setup.modules:
        unseen: engine.changes.Changes = _unseen_changes(ctx, carried, module.name)
        if unseen:
            engine.output.print_list(f"on_change of {module.name} would see:", unseen.summary(), one_per_line=True)


def run(setup: engine.setup.Setup, args: argparse.Namespace) -> None:
    dry: bool = args.dry_run
    hooks: bool = not args.no_hooks and not dry
    setup.aur.upgrade_devel = args.aur_upgrade_devel

    state: engine.state.State = _load_state(dry)
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
        engine.steps.STEPS[step](ctx)
        _diff_declarations(ctx, engine.steps.KINDS.get(step, ()))
        if not dry:
            _save_unseen(ctx, carried)

    if "users" in steps and not dry:
        engine.steps.users.finish(ctx)

    if dry:
        _report_dry_run(ctx, carried, new, disabled)
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

    # decman's store is root-only, so importing it needs root even alongside --dry-run.
    if (not args.dry_run or args.import_decman) and not engine.command.is_root():
        _reexec_as_root()

    if args.import_decman:
        if not engine.state.decman_store_exists():
            engine.output.print_error(f"There is no decman store at {engine.state.DECMAN_STORE}.")
            sys.exit(1)
        engine.state.import_decman_store().save()
        engine.output.print_info(f"Saved to {engine.state.STATE_FILE}.")
        return

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
    except (
        engine.aur.AurError,
        engine.steps.files.DuplicateTargetError,
        PermissionError,
        RuntimeError,
        ValueError,
    ) as error:
        engine.output.print_error(str(error))
        if args.debug:
            traceback.print_exc()
        sys.exit(1)
