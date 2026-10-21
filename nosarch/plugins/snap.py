"""Decman plugin for managing Snap packages.

Register it as follows, since it is not installed as a Python package:
```
    import decman
    from plugins import snap

    decman.plugins["snap"] = snap.plugin
    decman.execution_order += ["snap"]
```
"""

import shutil
from typing import override

import decman
import decman.core.command
import decman.core.error
import decman.core.module
import decman.core.output
import decman.core.store
from decman.plugins import Plugin, run_methods_with_attribute

# Base snaps every other snap is built on. Removing one breaks the rest. `snap list` marks them `base` in its Notes
# column. The name check stands on its own so a removal decision never rests on a single column.
_BASE_SNAP_NAMES: tuple[str, ...] = ("bare", "snapd")
_BASE_SNAP_PREFIXES: tuple[str, ...] = ("core", "kernel-")


def snaps(fn):
    """
    Annotate that this function returns the snap names that should be installed with default confinement, mapped to
    the channel each should track.

    Return type of `fn`: `dict[str, str]`
    """
    fn.__snap__snaps__ = True
    return fn


def classic_snaps(fn):
    """
    Annotate that this function returns the snap names that should be installed with `classic` confinement, mapped to
    the channel each should track.

    Return type of `fn`: `dict[str, str]`
    """
    fn.__snap__classic_snaps__ = True
    return fn


def _is_valid_channel(channel: str) -> bool:
    """
    Whether a channel can be passed to `snap install --channel`.

    Channels are defined by publishers, not a fixed list. It has to be a single word that cannot read as a flag.
    """
    return bool(channel) and not channel.startswith("-") and not any(c.isspace() for c in channel)


def _is_base_snap(name: str, notes: str) -> bool:
    """Whether a snap is one snapd needs for itself, and must never be removed."""
    return notes == "base" or name in _BASE_SNAP_NAMES or name.startswith(_BASE_SNAP_PREFIXES)


def _is_socket_active() -> bool:
    """
    Whether snapd's socket is accepting connections.
    """
    code, _ = decman.core.command.run(["systemctl", "is-active", "--quiet", "snapd.socket"])
    return code == 0


def _parse_list(output: str) -> dict[str, str]:
    """
    Turns `snap list` output into a mapping of snap name to its Notes column.

    The first line is a header, which is skipped. Snap names, versions and publishers never
    contain spaces, so Notes is only present when a line carries all six columns.
    """
    snaps: dict[str, str] = {}

    for line in output.strip().split("\n")[1:]:
        fields: list[str] = line.split()
        if not fields:
            continue
        snaps[fields[0]] = fields[5] if len(fields) >= 6 else ""

    return snaps


class Snap(Plugin):
    """
    Plugin that manages snaps added directly to the plugin's collections or declared by modules via `@snap.snaps` and
    `@snap.classic_snaps`.
    """

    NAME: str = "snap"

    def __init__(self) -> None:
        self.snaps: dict[str, str] = {}
        self.classic_snaps: dict[str, str] = {}
        self.ignored_snaps: set[str] = set()

        # When True, run `snap refresh` on every apply. Off by default.
        # `snapd.timer` already refreshes on its own schedule, so this would only duplicate that work.
        self.upgrade: bool = False

    @override
    def available(self) -> bool:
        return shutil.which("snap") is not None

    @override
    def process_modules(self, store: decman.core.store.Store, modules: list[decman.core.module.Module]) -> None:
        store.ensure("snaps_for_module", {})
        store.ensure("classic_snaps_for_module", {})

        for mod in modules:
            store["snaps_for_module"].setdefault(mod.name, {})
            store["classic_snaps_for_module"].setdefault(mod.name, {})

            mod_snaps = {
                name: channel
                for channels in run_methods_with_attribute(mod, "__snap__snaps__")
                for name, channel in channels.items()
            }
            mod_classic = {
                name: channel
                for channels in run_methods_with_attribute(mod, "__snap__classic_snaps__")
                for name, channel in channels.items()
            }

            if store["snaps_for_module"][mod.name] != mod_snaps:
                mod._changed = True
                decman.core.output.print_debug(f"Module '{mod.name}' set to changed due to modified snaps.")

            if store["classic_snaps_for_module"][mod.name] != mod_classic:
                mod._changed = True
                decman.core.output.print_debug(f"Module '{mod.name}' set to changed due to modified classic snaps.")

            self.snaps.update(mod_snaps)
            self.classic_snaps.update(mod_classic)

            store["snaps_for_module"][mod.name] = mod_snaps
            store["classic_snaps_for_module"][mod.name] = mod_classic

    @override
    def apply(self, store: decman.core.store.Store, dry_run: bool = False, params: list[str] | None = None) -> bool:
        snap_bin: str | None = shutil.which("snap")
        if snap_bin is None:
            if dry_run:
                # snapd arrives during this very run, so a dry run of a first apply has nothing
                # to compare against. Report that instead of failing the run.
                decman.core.output.print_warning("Snap plugin: snapd is not installed, so snaps cannot be checked.")
                return True

            decman.core.output.print_error("Snap plugin: could not find the 'snap' executable.")
            return False

        declared: dict[str, tuple[bool, str]] = {name: (False, channel) for name, channel in self.snaps.items()}
        declared |= {name: (True, channel) for name, channel in self.classic_snaps.items()}

        # Decman's systemd plugin only enables units, which does not start it, so on the run that installs snapd,
        # nothing is listening on the socket yet and every snap command fails to reach the daemon. The module enables
        # snapd.socket for the next boot but the daemon is needed now.
        if not _is_socket_active():
            if dry_run:
                decman.core.output.print_warning("Snap plugin: snapd is not running, so snaps cannot be checked.")
                return True

            self._start_daemon()

        # A snap declared both ways cannot be installed both ways, and `snap list` reports no
        # confinement to reconcile against, so this is caught before anything is installed.
        both: set[str] = self.snaps.keys() & self.classic_snaps.keys()
        if both:
            decman.core.output.print_error(
                f"Snap plugin: these snaps are declared both confined and classic: {', '.join(sorted(both))}"
            )
            return False

        for name, (_, channel) in sorted(declared.items()):
            if not _is_valid_channel(channel):
                decman.core.output.print_error(f"Snap plugin: snap '{name}' has an invalid channel '{channel}'.")
                return False

        interface = SnapInterface(SnapCommands(snap_bin))

        try:
            self._apply_snaps(interface, declared, dry_run)
        except decman.core.error.CommandFailedError as error:
            decman.core.output.print_error("Running a snap command failed.")
            decman.core.output.print_error(str(error))
            if error.output:
                decman.core.output.print_command_output(error.output)
            decman.core.output.print_traceback()
            return False
        return True

    @staticmethod
    def _start_daemon() -> None:
        """
        Starts snapd's socket so the client has something to connect to.

        The AppArmor unit is started too since it is a oneshot that only loads profiles once, and leaving it for the
        next boot means snaps run unconfined until then.

        `check=False` because the daemon not coming up is reported by the first snap command, which fails with a
        better message than systemctl's would give here.
        """
        _ = decman.prg(["systemctl", "start", "snapd.socket", "snapd.apparmor.service"], check=False)

    def _apply_snaps(self, interface: "SnapInterface", declared: dict[str, tuple[bool, str]], dry_run: bool) -> None:
        # Maps snap name to the Notes column, which is how base snaps are told apart.
        installed: dict[str, str] = interface.installed_snaps()

        to_install: dict[str, tuple[bool, str]] = {
            name: entry for name, entry in declared.items() if name not in installed and name not in self.ignored_snaps
        }
        to_remove: set[str] = {
            name
            for name, notes in installed.items()
            if name not in declared and name not in self.ignored_snaps and not _is_base_snap(name, notes)
        }

        if to_remove:
            decman.core.output.print_list("Removing snap packages:", sorted(to_remove))
            if not dry_run:
                interface.remove(to_remove)

        if to_install:
            decman.core.output.print_list("Installing snap packages:", sorted(to_install))
            if not dry_run:
                # The first snap command on a fresh install has to wait out snapd's base snaps
                # anyway, and installing into an unseeded store can fail. Wait for it explicitly.
                interface.wait_seeded()
                for name, (classic, channel) in to_install.items():
                    interface.install(name, classic, channel)

        # Refreshed last, since installing already brings a snap to its newest revision.
        if self.upgrade and not dry_run:
            decman.core.output.print_summary("Refreshing snap packages.")
            interface.refresh()


class SnapCommands:
    """Builds the `snap` command lines."""

    def __init__(self, snap: str) -> None:
        self._snap: str = snap

    def list_snaps(self) -> list[str]:
        """Outputs one installed snap per line, columns separated by whitespace."""
        return [self._snap, "list"]

    def wait_seeded(self) -> list[str]:
        """Blocks until snapd has installed the base snaps the store needs."""
        return [self._snap, "wait", "system", "seed.loaded"]

    def install(self, name: str, classic: bool, channel: str) -> list[str]:
        args = [self._snap, "install"]

        if classic:
            args.append("--classic")

        return args + [f"--channel={channel}", name]

    def remove(self, pkgs: set[str]) -> list[str]:
        return [self._snap, "remove"] + sorted(pkgs)

    def refresh(self) -> list[str]:
        """Refreshes every installed snap."""
        return [self._snap, "refresh"]


class SnapInterface:
    """
    High level interface for running snap commands.

    On failure methods raise a `CommandFailedError`.
    """

    # Snap localises its output. Pinning the locale keeps parsing stable whatever the system is set to.
    # Also drops snap's progress spinners out of what we read back.
    _ENV: dict[str, str] = {"LC_ALL": "C"}

    def __init__(self, commands: SnapCommands) -> None:
        self._commands: SnapCommands = commands

    def installed_snaps(self) -> dict[str, str]:
        """Returns the installed snaps, each mapped to the value of its Notes column."""
        cmd = self._commands.list_snaps()
        _, out = decman.core.command.check_run_result(cmd, decman.core.command.run(cmd, env_overrides=self._ENV))
        return _parse_list(out)

    def wait_seeded(self) -> None:
        _ = decman.core.command.prg(self._commands.wait_seeded(), env_overrides=self._ENV)

    def install(self, name: str, classic: bool, channel: str) -> None:
        _ = decman.core.command.prg(self._commands.install(name, classic, channel), env_overrides=self._ENV)

    def remove(self, pkgs: set[str]) -> None:
        if pkgs:
            _ = decman.core.command.prg(self._commands.remove(pkgs), env_overrides=self._ENV)

    def refresh(self) -> None:
        _ = decman.core.command.prg(self._commands.refresh(), env_overrides=self._ENV)


# Singleton instance. Register it (see the module docstring).
plugin: Snap = Snap()
