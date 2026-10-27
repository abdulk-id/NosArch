"""Installs and removes snaps. Refreshing is left to `snapd.timer`."""

import shutil

import engine.command
import engine.module
import engine.output
import engine.setup

# Base snaps every other snap is built on. Removing one breaks the rest. `snap list` marks them `base` in its Notes
# column. The name check stands on its own so a removal decision never rests on a single column.
_BASE_SNAP_NAMES: tuple[str, ...] = ("bare", "snapd")
_BASE_SNAP_PREFIXES: tuple[str, ...] = ("core", "kernel-")

# Snap localizes its output. Pinning the locale keeps parsing stable, and also drops the progress spinners.
_ENV: dict[str, str] = {"LC_ALL": "C"}

# Mark a module method as returning `dict[str, str]` of snap name to the channel it tracks.
snaps = engine.module.declares("snap")
classic_snaps = engine.module.declares("snap_classic")


def _is_valid_channel(channel: str) -> bool:
    """Channels are defined by publishers, not a fixed list. It has to be a single word that cannot read as a flag."""
    return bool(channel) and not channel.startswith("-") and not any(c.isspace() for c in channel)


def _is_base_snap(name: str, notes: str) -> bool:
    return notes == "base" or name in _BASE_SNAP_NAMES or name.startswith(_BASE_SNAP_PREFIXES)


def _installed() -> dict[str, str]:
    """
    Installed snap names, each mapped to its Notes column.

    The first line is a header. Names, versions, and publishers never contain spaces, so Notes is only present when a
    line carries all six columns.
    """

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

    # `snap list` reports no confinement to reconcile against, so this is caught before anything is installed.
    both: set[str] = confined.keys() & classic.keys()
    if both:
        raise RuntimeError(f"These snaps are declared both confined and classic: {', '.join(sorted(both))}")

    declared: dict[str, tuple[bool, str]] = {name: (False, channel) for name, channel in confined.items()}
    declared |= {name: (True, channel) for name, channel in classic.items()}

    for name, (_, channel) in sorted(declared.items()):
        if not _is_valid_channel(channel):
            raise RuntimeError(f"Snap '{name}' has an invalid channel '{channel}'.")

    if shutil.which("snap") is None:
        # snapd arrives during this very run, so a dry run of a first apply has nothing to compare against.
        engine.output.print_warning("snapd is not installed yet, so snaps cannot be checked.")
        if not ctx.dry_run:
            raise RuntimeError("The snap command is missing.")
        return

    # The systemd step only enables units, which does not start them. On the run that installs snapd nothing is
    # listening on the socket yet, and every snap command fails to reach the daemon. The AppArmor unit is a oneshot
    # that loads profiles once, and left for the next boot, snaps would run unconfined until then.
    if not engine.command.succeeds(["systemctl", "is-active", "--quiet", "snapd.socket"]):
        if ctx.dry_run:
            engine.output.print_warning("snapd is not running, so snaps cannot be checked.")
            return
        engine.command.run(["systemctl", "start", "snapd.socket", "snapd.apparmor.service"], check=False)

    installed: dict[str, str] = _installed()
    to_install: dict[str, tuple[bool, str]] = {name: entry for name, entry in declared.items() if name not in installed}
    to_remove: set[str] = {
        name for name, notes in installed.items() if name not in declared and not _is_base_snap(name, notes)
    }

    engine.output.print_list("Removing snaps:" if not ctx.dry_run else "Snaps to remove:", to_remove)
    engine.output.print_list("Installing snaps:" if not ctx.dry_run else "Snaps to install:", set(to_install))

    if ctx.dry_run:
        return

    if to_remove:
        engine.command.run(["snap", "remove", *sorted(to_remove)], env=_ENV)

    if to_install:
        # Installing into a store that has not finished seeding can fail.
        engine.command.run(["snap", "wait", "system", "seed.loaded"], env=_ENV)
        for name, (is_classic, channel) in sorted(to_install.items()):
            engine.command.run(
                ["snap", "install", *(["--classic"] if is_classic else []), f"--channel={channel}", name], env=_ENV
            )
