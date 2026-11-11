"""
The scratch machine the engine tests run on: a recorder for every command, a fake account database, and modules that log
their hooks.

Files go under a temporary directory and the state file lives there too. No command ever really runs: `nosarch.engine.command.run`
is replaced by `Commands`, so a step that would call `systemctl` or `useradd` only leaves its argument list behind. Tests
of the command runner itself use `real_run`.
"""

from __future__ import annotations

import argparse
import grp
import os
import pwd
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

import pytest

import nosarch.engine
import nosarch.engine.app
import nosarch.engine.changes
import nosarch.engine.command
import nosarch.engine.output
import nosarch.engine.state
from nosarch.engine.command import run as real_run
from nosarch.engine.steps import systemd

__all__ = ["Accounts", "Box", "Call", "Commands", "Rec", "real_run"]


# --- Commands ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Call:
    argv: list[str]
    user: str | None
    check: bool
    capture: bool


class Commands:
    """Stands in for `nosarch.engine.command.run`: records every call, succeeds, and fails the ones a test says to fail."""

    def __init__(self, log: list[str]) -> None:
        self.calls: list[Call] = []
        self._log: list[str] = log
        self._failures: list[tuple[list[str], int]] = []
        self._effects: list[tuple[list[str], Callable[[list[str]], None]]] = []

    def argv(self) -> list[list[str]]:
        return [call.argv for call in self.calls]

    def fail(self, *prefix: str, code: int = 1) -> None:
        """Makes every command that starts with `prefix` exit with `code`."""
        self._failures.append((list(prefix), code))

    def on(self, *prefix: str, effect: Callable[[list[str]], None]) -> None:
        """Runs `effect` with the argument list whenever a command that starts with `prefix` succeeds."""
        self._effects.append((list(prefix), effect))

    def reset(self) -> None:
        self.calls.clear()

    def __call__(
        self,
        cmd: list[str],
        *,
        user: str | None = None,
        env: dict[str, str] | None = None,
        pass_environment: bool = True,
        capture: bool = False,
        check: bool = True,
        cwd: str | None = None,
    ) -> str:
        self.calls.append(Call(list(cmd), user, check, capture))
        self._log.append("cmd " + " ".join(cmd))

        for prefix, code in self._failures:
            if cmd[: len(prefix)] == prefix:
                if check:
                    raise nosarch.engine.command.CommandFailedError(cmd, code, "" if capture else None)
                return ""

        for prefix, effect in self._effects:
            if cmd[: len(prefix)] == prefix:
                effect(cmd)
        return ""


# --- Accounts ---------------------------------------------------------------------------------------------------------
class Accounts:
    """
    A fake /etc/passwd and /etc/group, and a `useradd`, `usermod` and `userdel` that edit it.

    It starts with root only. The engine reads accounts through `pwd` and `grp`, so a test can have `alice` exist, or
    not, without touching the machine.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch, commands: Commands) -> None:
        self.users: dict[str, pwd.struct_passwd] = {}
        self.groups: dict[str, tuple[int, set[str]]] = {}

        self.add_user("root", 0, 0, "/root", "/bin/sh")

        monkeypatch.setattr(pwd, "getpwnam", self._getpwnam)
        monkeypatch.setattr(pwd, "getpwuid", self._getpwuid)
        monkeypatch.setattr(grp, "getgrnam", self._getgrnam)
        monkeypatch.setattr(grp, "getgrgid", self._getgrgid)
        monkeypatch.setattr(grp, "getgrall", self._getgrall)

        commands.on("useradd", effect=self._useradd)
        commands.on("usermod", effect=self._usermod)
        commands.on("userdel", effect=self._userdel)

    # What the system says.
    def add_group(self, name: str, gid: int, members: Iterable[str] = ()) -> None:
        self.groups[name] = (gid, set(members))

    def add_user(
        self, name: str, uid: int, gid: int, home: str = "/", shell: str = "/bin/sh", groups: Iterable[str] = ()
    ) -> None:
        self.users[name] = pwd.struct_passwd((name, "x", uid, gid, "", home, shell))
        if all(gid != existing for existing, _ in self.groups.values()):
            self.add_group(name, gid)
        for group in groups:
            self.groups[group][1].add(name)

    def has_user(self, name: str) -> bool:
        return name in self.users

    def members(self, group: str) -> set[str]:
        return set(self.groups[group][1])

    def _getpwnam(self, name: str) -> pwd.struct_passwd:
        try:
            return self.users[name]
        except KeyError:
            raise KeyError(f"getpwnam(): name not found: {name!r}") from None

    def _getpwuid(self, uid: int) -> pwd.struct_passwd:
        for entry in self.users.values():
            if entry.pw_uid == uid:
                return entry
        raise KeyError(f"getpwuid(): uid not found: {uid}")

    def _struct(self, name: str) -> grp.struct_group:
        gid, members = self.groups[name]
        return grp.struct_group((name, "x", gid, sorted(members)))

    def _getgrnam(self, name: str) -> grp.struct_group:
        try:
            return self._struct(name)
        except KeyError:
            raise KeyError(f"getgrnam(): name not found: {name!r}") from None

    def _getgrgid(self, gid: int) -> grp.struct_group:
        for name, (existing, _) in self.groups.items():
            if existing == gid:
                return self._struct(name)
        raise KeyError(f"getgrgid(): gid not found: {gid}")

    def _getgrall(self) -> list[grp.struct_group]:
        return [self._struct(name) for name in self.groups]

    # What the commands do.
    @staticmethod
    def _option(cmd: list[str], flag: str) -> str | None:
        return cmd[cmd.index(flag) + 1] if flag in cmd else None

    def _next_id(self, system: bool) -> int:
        taken: set[int] = {entry.pw_uid for entry in self.users.values()}
        return next(number for number in range(100 if system else 1000, 60000) if number not in taken)

    def _useradd(self, cmd: list[str]) -> None:
        name: str = cmd[-1]
        group: str | None = self._option(cmd, "--gid")
        if group is not None and group not in self.groups:
            raise nosarch.engine.command.CommandFailedError(cmd, 6, None)
        if "--user-group" in cmd or group is None:
            self.add_group(name, self._next_id("--system" in cmd))
            group = name
        uid: int = self._next_id("--system" in cmd)
        self.users[name] = pwd.struct_passwd(
            (
                name,
                "x",
                uid,
                self.groups[group][0],
                "",
                self._option(cmd, "--home-dir") or f"/home/{name}",
                self._option(cmd, "--shell") or "/bin/sh",
            )
        )
        for member_of in (self._option(cmd, "--groups") or "").split(","):
            if member_of:
                self.groups[member_of][1].add(name)

    def _usermod(self, cmd: list[str]) -> None:
        name: str = cmd[-1]
        entry: pwd.struct_passwd = self.users[name]
        gid: int = self.groups[self._option(cmd, "--gid")][0] if "--gid" in cmd else entry.pw_gid  # pyright: ignore[reportArgumentType]
        home: str = self._option(cmd, "--home") or entry.pw_dir
        shell: str = self._option(cmd, "--shell") or entry.pw_shell
        self.users[name] = pwd.struct_passwd((name, "x", entry.pw_uid, gid, "", home, shell))

        if "--groups" in cmd:
            for _, members in self.groups.values():
                members.discard(name)
            for member_of in (self._option(cmd, "--groups") or "").split(","):
                if member_of:
                    self.groups[member_of][1].add(name)

    def _userdel(self, cmd: list[str]) -> None:
        name: str = cmd[-1]
        del self.users[name]
        for _, members in self.groups.values():
            members.discard(name)


# --- Modules ----------------------------------------------------------------------------------------------------------
class Rec(nosarch.engine.Module):
    """
    A module that writes every hook that runs to the shared log, as `before_update:name`.

    `actions` maps a hook name to a function that runs when the hook fires, which is how a test makes a hook raise,
    or write a file. `changes` holds what each `on_change` was told.
    """

    def __init__(
        self,
        name: str,
        log: list[str],
        *,
        files: dict[str, nosarch.engine.File] | None = None,
        directories: dict[str, nosarch.engine.Directory] | None = None,
        symlinks: dict[str, str | nosarch.engine.Symlink] | None = None,
        variables: dict[str, str] | None = None,
        units: set[str] | None = None,
        user_units: dict[str, set[str]] | None = None,
        actions: dict[str, Callable[[], None]] | None = None,
    ) -> None:
        super().__init__(name)
        self._log: list[str] = log
        self._files: dict[str, nosarch.engine.File] = files or {}
        self._directories: dict[str, nosarch.engine.Directory] = directories or {}
        self._symlinks: dict[str, str | nosarch.engine.Symlink] = symlinks or {}
        self._variables: dict[str, str] = variables or {}
        self._units: set[str] = units or set()
        self._user_units: dict[str, set[str]] = user_units or {}
        self._actions: dict[str, Callable[[], None]] = actions or {}
        self.changes: list[nosarch.engine.Changes] = []

    def _hook(self, event: str) -> None:
        self._log.append(f"{event}:{self.name}")
        if event in self._actions:
            self._actions[event]()

    @override
    def before_update(self) -> None:
        self._hook("before_update")

    @override
    def on_enable(self) -> None:
        self._hook("on_enable")

    @override
    def on_change(self, changes: nosarch.engine.Changes) -> None:
        self.changes.append(changes)
        self._hook("on_change")

    @override
    def after_update(self) -> None:
        self._hook("after_update")

    @override
    def on_disable(self) -> None:
        self._hook("on_disable")

    @override
    def files(self) -> dict[str, nosarch.engine.File]:
        return dict(self._files)

    @override
    def directories(self) -> dict[str, nosarch.engine.Directory]:
        return dict(self._directories)

    @override
    def symlinks(self) -> dict[str, str | nosarch.engine.Symlink]:
        return dict(self._symlinks)

    @override
    def file_variables(self) -> dict[str, str]:
        return dict(self._variables)

    @systemd.units
    def _declared_units(self) -> set[str]:
        return set(self._units)

    @systemd.user_units
    def _declared_user_units(self) -> dict[str, set[str]]:
        return {user: set(units) for user, units in self._user_units.items()}


# --- The scratch machine ----------------------------------------------------------------------------------------------
class Box:
    """A scratch machine: a directory to deploy into, the engine's state, and what the engine did."""

    def __init__(self, root: Path, log: list[str], commands: Commands) -> None:
        self.root: Path = root
        self.log: list[str] = log
        self.commands: Commands = commands

    @property
    def hooks(self) -> list[str]:
        """The hooks that ran in the last `apply`, in order, as `before_update:name`."""
        return [entry for entry in self.log if not entry.startswith("cmd ")]

    @property
    def argv(self) -> list[list[str]]:
        """The commands the last `apply` ran, in order."""
        return self.commands.argv()

    def path(self, relative: str) -> str:
        return str(self.root / relative)

    def write(self, relative: str, content: str | bytes, mode: int | None = None) -> str:
        target: Path = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        if mode is not None:
            target.chmod(mode)
        return str(target)

    def read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def mode(self, relative: str) -> int:
        return (self.root / relative).stat().st_mode & 0o7777

    def exists(self, relative: str) -> bool:
        return os.path.lexists(self.root / relative)

    def state(self) -> nosarch.engine.state.State | None:
        return nosarch.engine.state.load()

    def rec(self, name: str, **declarations: Any) -> Rec:
        return Rec(name, self.log, **declarations)

    def apply(
        self,
        *modules: nosarch.engine.Module,
        disabled: Iterable[nosarch.engine.Module] = (),
        users: Iterable[nosarch.engine.User] = (),
        steps: Iterable[str] = ("files",),
        dry_run: bool = False,
        only: Iterable[str] = (),
        skip: Iterable[str] = (),
        no_hooks: bool = False,
    ) -> None:
        """
        One run, as `python -m nosarch` does it. An error the engine raises reaches the test.

        `self.log` and `self.commands` start empty, so they describe this run only.
        """
        self.log.clear()
        self.commands.reset()

        setup: nosarch.engine.Setup = nosarch.engine.Setup(steps=list(steps))
        for module in modules:
            setup.add(module)
        for module in disabled:
            setup.add(module, enabled=False)
        setup.users += list(users)

        nosarch.engine.app.run(
            setup,
            argparse.Namespace(
                dry_run=dry_run, only=list(only), skip=list(skip), no_hooks=no_hooks, aur_upgrade_devel=False
            ),
        )
