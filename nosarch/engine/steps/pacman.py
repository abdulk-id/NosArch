import os
import re

import nosarch.engine.command
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.pacman_db
import nosarch.engine.setup

packages = nosarch.engine.module.declares("pacman")

_SECTION: re.Pattern[str] = re.compile(r"^\[([^]]+)]$")
_DEFAULT_DB_PATH: str = "/var/lib/pacman/"


def missing_sync_databases(conf_path: str = "/etc/pacman.conf") -> list[str]:
    """Enabled repositories whose database file is not on disk yet."""
    try:
        repos, db_path = _pacman_layout(conf_path)
    except OSError:
        return []

    sync_dir: str = os.path.join(db_path, "sync")
    return [repo for repo in repos if not os.path.exists(os.path.join(sync_dir, f"{repo}.db"))]


def _pacman_layout(conf_path: str) -> tuple[list[str], str]:
    repos: list[str] = []
    db_path: str = _DEFAULT_DB_PATH
    in_options: bool = False

    with open(conf_path, encoding="utf-8") as conf:
        for raw in conf:
            line: str = raw.split("#", 1)[0].strip()
            if not line:
                continue

            section: re.Match[str] | None = _SECTION.match(line)
            if section:
                name: str = section.group(1)
                in_options = name == "options"
                if not in_options:
                    repos.append(name)
                continue

            if not in_options:
                continue

            key, _, value = line.partition("=")
            if key.strip() == "DBPath" and value.strip():
                db_path = value.strip()

    return repos, db_path


def run(ctx: nosarch.engine.setup.Context) -> None:
    # The files step may have just enabled a repository, such as multilib. Pacman warns
    # "database file for '…' does not exist (use -Sy to download)" on every command that is
    # not a sync, including the queries below, until that database has been downloaded.
    if not ctx.dry_run and missing_sync_databases():
        nosarch.engine.output.print_summary("Synchronizing package databases.")
        nosarch.engine.command.run(["pacman", "-Sy", "--noconfirm"])

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
        nosarch.engine.command.run(["pacman", "-Rs", "--noconfirm", *sorted(remove)])

    nosarch.engine.output.print_list("Marking packages nothing declares as dependencies:", demote)
    if demote and not ctx.dry_run:
        nosarch.engine.command.run(["pacman", "-D", "--asdeps", *sorted(demote)])

    if ctx.dry_run:
        nosarch.engine.output.print_info("Would upgrade the system with `pacman -Syu`.")
    else:
        nosarch.engine.output.print_summary("Upgrading packages.")
        nosarch.engine.command.run(["pacman", "-Syu", "--noconfirm"])

    nosarch.engine.output.print_list(
        "Installing pacman packages:" if not ctx.dry_run else "Pacman packages to install:", to_install
    )
    if to_install and not ctx.dry_run:
        nosarch.engine.command.run(["pacman", "-S", "--needed", "--noconfirm", *sorted(to_install)])
        nosarch.engine.command.run(["pacman", "-D", "--asexplicit", *sorted(to_install)], capture=True)
