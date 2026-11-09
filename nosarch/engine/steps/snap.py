import shutil

import engine.command
import engine.module
import engine.output
import engine.setup

_BASE_SNAP_NAMES: tuple[str, ...] = ("bare", "snapd")
_BASE_SNAP_PREFIXES: tuple[str, ...] = ("core", "kernel-")

_ENV: dict[str, str] = {"LC_ALL": "C"}

snaps = engine.module.declares("snap")
classic_snaps = engine.module.declares("snap_classic")


def _installed() -> dict[str, str]:
    output: str = engine.command.run(["snap", "list"], env=_ENV, capture=True)
    installed: dict[str, str] = {}
    for line in output.strip().splitlines()[1:]:
        fields: list[str] = line.split()
        if fields:
            installed[fields[0]] = fields[5] if len(fields) >= 6 else ""
    return installed


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking snaps.")

    confined: dict[str, str] = ctx.declared("snap")
    classic: dict[str, str] = ctx.declared("snap_classic")

    both: set[str] = confined.keys() & classic.keys()
    if both:
        raise RuntimeError(f"These snaps are declared both confined and classic: {', '.join(sorted(both))}")

    declared: dict[str, tuple[bool, str]] = {name: (False, channel) for name, channel in confined.items()}
    declared |= {name: (True, channel) for name, channel in classic.items()}

    for name, (_, channel) in sorted(declared.items()):
        if not channel or channel.startswith("-") or any(character.isspace() for character in channel):
            raise RuntimeError(f"Snap '{name}' has an invalid channel '{channel}'.")

    if shutil.which("snap") is None:
        engine.output.print_warning("snapd is not installed yet, so snaps cannot be checked.")
        if not ctx.dry_run:
            raise RuntimeError("The snap command is missing.")
        return

    if not engine.command.succeeds(["systemctl", "is-active", "--quiet", "snapd.socket"]):
        if ctx.dry_run:
            engine.output.print_warning("snapd is not running, so snaps cannot be checked.")
            return
        engine.command.run(["systemctl", "start", "snapd.socket", "snapd.apparmor.service"], check=False)

    installed: dict[str, str] = _installed()
    to_install: dict[str, tuple[bool, str]] = {name: entry for name, entry in declared.items() if name not in installed}
    to_remove: set[str] = {
        name
        for name, notes in installed.items()
        if name not in declared
        and notes != "base"
        and name not in _BASE_SNAP_NAMES
        and not name.startswith(_BASE_SNAP_PREFIXES)
    }

    engine.output.print_list("Removing snaps:" if not ctx.dry_run else "Snaps to remove:", to_remove)
    engine.output.print_list("Installing snaps:" if not ctx.dry_run else "Snaps to install:", set(to_install))

    if ctx.dry_run:
        return

    if to_remove:
        engine.command.run(["snap", "remove", *sorted(to_remove)], env=_ENV)

    if to_install:
        engine.command.run(["snap", "wait", "system", "seed.loaded"], env=_ENV)
        for name, (is_classic, channel) in sorted(to_install.items()):
            engine.command.run(
                ["snap", "install", *(["--classic"] if is_classic else []), f"--channel={channel}", name], env=_ENV
            )
