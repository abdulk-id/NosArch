import nosarch.engine.command
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.pacman_db
import nosarch.engine.setup

packages = nosarch.engine.module.declares("pacman")


def run(ctx: nosarch.engine.setup.Context) -> None:
    nosarch.engine.output.print_summary("Checking pacman packages.")

    declared: set[str] = ctx.declared("pacman")
    installed: dict[str, nosarch.engine.pacman_db.LocalPackage] = nosarch.engine.pacman_db.local_packages()

    explicit_native: set[str] = {name for name, pkg in installed.items() if pkg.explicit and pkg.native}
    explicit_foreign: set[str] = {name for name, pkg in installed.items() if pkg.explicit and not pkg.native}
    orphans: set[str] = nosarch.engine.pacman_db.orphans(installed, native=True)

    remove, demote = nosarch.engine.pacman_db.split_removals(
        installed, (explicit_native | orphans) - declared, keep=declared | explicit_foreign
    )
    demote -= orphans

    to_install: set[str] = {name for name in declared if name not in installed or not installed[name].explicit}

    nosarch.engine.output.print_list(
        "Removing pacman packages:" if not ctx.dry_run else "Pacman packages to remove:", remove
    )
    if remove and not ctx.dry_run:
        nosarch.engine.command.run(["pacman", "-Rs", *sorted(remove)])

    nosarch.engine.output.print_list("Marking packages nothing declares as dependencies:", demote)
    if demote and not ctx.dry_run:
        nosarch.engine.command.run(["pacman", "-D", "--asdeps", *sorted(demote)])

    if ctx.dry_run:
        nosarch.engine.output.print_info("Would upgrade the system with `pacman -Syu`.")
    else:
        nosarch.engine.output.print_summary("Upgrading packages.")
        nosarch.engine.command.run(["pacman", "-Syu"])

    nosarch.engine.output.print_list(
        "Installing pacman packages:" if not ctx.dry_run else "Pacman packages to install:", to_install
    )
    if to_install and not ctx.dry_run:
        nosarch.engine.command.run(["pacman", "-S", "--needed", *sorted(to_install)])
        nosarch.engine.command.run(["pacman", "-D", "--asexplicit", *sorted(to_install)], capture=True)
