"""Installs the declared repository packages, upgrades the system, and removes what nothing declares."""

import engine.command
import engine.module
import engine.output
import engine.pacman_db
import engine.setup

# Marks a module method as returning `set[str]` of repository package names.
packages = engine.module.declares("pacman")


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking pacman packages.")

    declared: set[str] = ctx.declared("pacman")
    installed: dict[str, engine.pacman_db.LocalPackage] = engine.pacman_db.local_packages()

    explicit_native: set[str] = {name for name, pkg in installed.items() if pkg.explicit and pkg.native}
    explicit_foreign: set[str] = {name for name, pkg in installed.items() if pkg.explicit and not pkg.native}
    orphans: set[str] = engine.pacman_db.orphans(installed, native=True)

    # Foreign packages are kept here: whatever they depend on stays, and the AUR step decides about them.
    remove, demote = engine.pacman_db.split_removals(
        installed, (explicit_native | orphans) - declared, keep=declared | explicit_foreign
    )
    # Already a dependency, nothing to mark.
    demote -= orphans

    to_install: set[str] = {name for name in declared if name not in installed or not installed[name].explicit}

    engine.output.print_list("Removing pacman packages:" if not ctx.dry_run else "Pacman packages to remove:", remove)
    if remove and not ctx.dry_run:
        engine.command.run(["pacman", "-Rs", *sorted(remove)])

    engine.output.print_list("Marking packages nothing declares as dependencies:", demote)
    if demote and not ctx.dry_run:
        engine.command.run(["pacman", "-D", "--asdeps", *sorted(demote)])

    if ctx.dry_run:
        engine.output.print_info("Would upgrade the system with `pacman -Syu`.")
    else:
        engine.output.print_summary("Upgrading packages.")
        engine.command.run(["pacman", "-Syu"])

    engine.output.print_list(
        "Installing pacman packages:" if not ctx.dry_run else "Pacman packages to install:", to_install
    )
    if to_install and not ctx.dry_run:
        engine.command.run(["pacman", "-S", "--needed", *sorted(to_install)])
        # `--needed` skips what is installed already, including what came in as a dependency.
        engine.command.run(["pacman", "-D", "--asexplicit", *sorted(to_install)], capture=True)
