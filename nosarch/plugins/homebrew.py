"""Decman plugin for managing Homebrew formulae, casks and taps.

- Homebrew refuses to run as root, so every `brew` invocation is executed as
  an unprivileged user (see `Homebrew.user`) via decman's command runner with
  `mimic_login=True`.

Register it as follows, since it is not installed as a Python package:
```
    import decman
    from plugins import homebrew

    homebrew.plugin.user = "username"
    decman.plugins["homebrew"] = homebrew.plugin
    decman.execution_order += ["homebrew"]
```
"""

import os
import pwd
import shutil
from typing import override

import decman.core.command as command
import decman.core.error as errors
import decman.core.module as module
import decman.core.output as output
import decman.core.store as _store

# Imported by name: decman's package rebinds the `decman.plugins` attribute to a
# dict, so `import decman.plugins as plugins` would not yield the submodule.
from decman.plugins import Plugin, run_methods_with_attribute

# Common Homebrew binary locations searched when `brew` is not on root's PATH.
# The default Linux install lives under the shared `linuxbrew` prefix.
_BREW_CANDIDATES: list[str] = [
    "/home/linuxbrew/.linuxbrew/bin/brew",
    "/opt/homebrew/bin/brew",  # Apple Silicon macOS
    "/usr/local/bin/brew",  # Intel macOS / older Linux prefix
]

# Taps that Homebrew manages implicitly and that should never be untapped by
# decman. Users can still declare and manage them explicitly if they want.
_PROTECTED_TAPS: set[str] = {"homebrew/core", "homebrew/cask"}


def formulae(fn):
    """
    Annotate that this function returns a set of Homebrew formulae that should be installed.

    Return type of `fn`: `set[str]`
    """
    fn.__homebrew__formulae__ = True
    return fn


def casks(fn):
    """
    Annotate that this function returns a set of Homebrew casks that should be installed.

    Return type of `fn`: `set[str]`
    """
    fn.__homebrew__casks__ = True
    return fn


def taps(fn):
    """
    Annotate that this function returns a set of Homebrew taps that should be added.

    Return type of `fn`: `set[str]`
    """
    fn.__homebrew__taps__ = True
    return fn


def _find_brew(user: str | None) -> str | None:
    """Locates the `brew` binary, checking the given user's home prefix as well."""
    candidates: list[str] = []

    on_path = shutil.which("brew")
    if on_path is not None:
        candidates.append(on_path)

    candidates += _BREW_CANDIDATES

    if user is not None:
        try:
            home = pwd.getpwnam(user).pw_dir
        except KeyError:
            home = None
        if home is not None:
            candidates.append(os.path.join(home, ".linuxbrew", "bin", "brew"))

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


class Homebrew(Plugin):
    """
    Plugin that manages Homebrew formulae, casks and taps added directly to the plugin's
    collections or declared by modules via `@homebrew.formulae`, `@homebrew.casks` and
    `@homebrew.taps`.

    Homebrew cannot run as root, so `user` must name the account that owns the Homebrew
    installation. It defaults to the invoking `sudo` user when unset.
    """

    NAME: str = "homebrew"

    def __init__(self) -> None:
        self.formulae: set[str] = set()
        self.casks: set[str] = set()
        self.taps: set[str] = set()
        self.ignored_formulae: set[str] = set()
        self.ignored_casks: set[str] = set()
        self.ignored_taps: set[str] = set()

        # Account to run `brew` as. Defaults to the sudo-invoking user.
        self.user: str | None = None

        # When True, run `brew upgrade` on every apply (mirrors the flatpak plugin).
        self.upgrade: bool = True

    @override
    def available(self) -> bool:
        return _find_brew(self.user or os.environ.get("SUDO_USER")) is not None

    @override
    def process_modules(self, store: _store.Store, modules: list[module.Module]) -> None:
        # These store keys track each module's declared state so that a module can be marked
        # as changed when its Homebrew declarations change between runs.
        store.ensure("brew_formulae_for_module", {})
        store.ensure("brew_casks_for_module", {})
        store.ensure("brew_taps_for_module", {})

        for mod in modules:
            store["brew_formulae_for_module"].setdefault(mod.name, set())
            store["brew_casks_for_module"].setdefault(mod.name, set())
            store["brew_taps_for_module"].setdefault(mod.name, set())

            mod_formulae = set().union(*run_methods_with_attribute(mod, "__homebrew__formulae__"))
            mod_casks = set().union(*run_methods_with_attribute(mod, "__homebrew__casks__"))
            mod_taps = set().union(*run_methods_with_attribute(mod, "__homebrew__taps__"))

            if store["brew_formulae_for_module"][mod.name] != mod_formulae:
                mod._changed = True
                output.print_debug(f"Module '{mod.name}' set to changed due to modified Homebrew formulae.")

            if store["brew_casks_for_module"][mod.name] != mod_casks:
                mod._changed = True
                output.print_debug(f"Module '{mod.name}' set to changed due to modified Homebrew casks.")

            if store["brew_taps_for_module"][mod.name] != mod_taps:
                mod._changed = True
                output.print_debug(f"Module '{mod.name}' set to changed due to modified Homebrew taps.")

            self.formulae |= mod_formulae
            self.casks |= mod_casks
            self.taps |= mod_taps

            store["brew_formulae_for_module"][mod.name] = mod_formulae
            store["brew_casks_for_module"][mod.name] = mod_casks
            store["brew_taps_for_module"][mod.name] = mod_taps

    @override
    def apply(self, store: _store.Store, dry_run: bool = False, params: list[str] | None = None) -> bool:
        user = self.user or os.environ.get("SUDO_USER")
        if user is None:
            output.print_error(
                "Homebrew plugin: no user configured. Set 'homebrew.plugin.user' since brew cannot run as root."
            )
            return False

        brew = _find_brew(user)
        if brew is None:
            output.print_error("Homebrew plugin: could not find the 'brew' executable.")
            return False

        hb = HomebrewInterface(HomebrewCommands(brew), user)

        try:
            self._apply_taps(hb, dry_run)
            self._apply_formulae(hb, dry_run)
            self._apply_casks(hb, dry_run)
        except errors.CommandFailedError as error:
            output.print_error("Running a Homebrew command failed.")
            output.print_error(str(error))
            if error.output:
                output.print_command_output(error.output)
            output.print_traceback()
            return False
        return True

    def _apply_taps(self, hb: "HomebrewInterface", dry_run: bool) -> None:
        current = hb.installed_taps()
        to_tap = self.taps - current - self.ignored_taps
        # Never untap protected taps or taps decman does not know about via `ignored_taps`.
        to_untap = current - self.taps - self.ignored_taps - _PROTECTED_TAPS

        # Taps must exist before installing the formulae/casks that live in them.
        if to_tap:
            output.print_list("Adding Homebrew taps:", sorted(to_tap))
            if not dry_run:
                hb.tap(to_tap)

        if to_untap:
            output.print_list("Removing Homebrew taps:", sorted(to_untap))
            if not dry_run:
                hb.untap(to_untap)

    def _apply_formulae(self, hb: "HomebrewInterface", dry_run: bool) -> None:
        installed = hb.installed_formulae()
        # Only formulae installed on request (not pulled in as dependencies) are candidates for
        # removal; orphaned dependencies are cleaned up afterwards with `brew autoremove`.
        on_request = hb.on_request_formulae()

        to_install = self.formulae - installed - self.ignored_formulae
        to_remove = on_request - self.formulae - self.ignored_formulae

        if to_remove:
            output.print_list("Removing Homebrew formulae:", sorted(to_remove))
            if not dry_run:
                hb.uninstall_formulae(to_remove)
                hb.autoremove()

        if self.upgrade:
            output.print_summary("Upgrading Homebrew packages.")
            if not dry_run:
                hb.upgrade()

        if to_install:
            output.print_list("Installing Homebrew formulae:", sorted(to_install))
            if not dry_run:
                hb.install_formulae(to_install)

    def _apply_casks(self, hb: "HomebrewInterface", dry_run: bool):
        installed = hb.installed_casks()
        to_install = self.casks - installed - self.ignored_casks
        to_remove = installed - self.casks - self.ignored_casks

        if to_remove:
            output.print_list("Removing Homebrew casks:", sorted(to_remove))
            if not dry_run:
                hb.uninstall_casks(to_remove)

        if to_install:
            output.print_list("Installing Homebrew casks:", sorted(to_install))
            if not dry_run:
                hb.install_casks(to_install)


class HomebrewCommands:
    """Builds the `brew` command lines. Kept separate to mirror the flatpak plugin."""

    def __init__(self, brew: str) -> None:
        self._brew: str = brew

    def list_formulae(self) -> list[str]:
        """Outputs one installed formula name per line, including dependencies."""
        return [self._brew, "list", "--formula", "-1"]

    def leaves_on_request(self) -> list[str]:
        """Outputs installed-on-request formulae that nothing else depends on, one per line."""
        return [self._brew, "leaves", "--installed-on-request"]

    def list_casks(self) -> list[str]:
        """Outputs one installed cask name per line."""
        return [self._brew, "list", "--cask", "-1"]

    def list_taps(self) -> list[str]:
        """Outputs one active tap per line."""
        return [self._brew, "tap"]

    def install_formulae(self, pkgs: set[str]) -> list[str]:
        return [self._brew, "install", "--formula"] + sorted(pkgs)

    def install_casks(self, pkgs: set[str]) -> list[str]:
        return [self._brew, "install", "--cask"] + sorted(pkgs)

    def uninstall_formulae(self, pkgs: set[str]) -> list[str]:
        return [self._brew, "uninstall", "--formula"] + sorted(pkgs)

    def uninstall_casks(self, pkgs: set[str]) -> list[str]:
        return [self._brew, "uninstall", "--cask"] + sorted(pkgs)

    def autoremove(self) -> list[str]:
        """Removes formulae that were only installed as now-unneeded dependencies."""
        return [self._brew, "autoremove"]

    def upgrade(self) -> list[str]:
        """Upgrades all installed formulae and casks."""
        return [self._brew, "upgrade"]

    def tap(self, tap: str) -> list[str]:
        return [self._brew, "tap", tap]

    def untap(self, tap: str) -> list[str]:
        return [self._brew, "untap", tap]


class HomebrewInterface:
    """
    High level interface for running Homebrew commands as an unprivileged user.

    On failure methods raise a `CommandFailedError`.
    """

    # Reduce noise from Homebrew's environment/analytics hints in decman output.
    _ENV: dict[str, str] = {"HOMEBREW_NO_ENV_HINTS": "1"}

    def __init__(self, commands: HomebrewCommands, user: str) -> None:
        self._commands: HomebrewCommands = commands
        self._user: str = user

    def _lines(self, cmd: list[str]) -> set[str]:
        _, out = command.check_run_result(
            cmd, command.run(cmd, user=self._user, mimic_login=True, env_overrides=self._ENV)
        )
        return {line for line in out.strip().split("\n") if line}

    def _run(self, cmd: list[str]) -> None:
        _ = command.prg(cmd, user=self._user, mimic_login=True, env_overrides=self._ENV)

    def installed_formulae(self) -> set[str]:
        return self._lines(self._commands.list_formulae())

    def on_request_formulae(self) -> set[str]:
        return self._lines(self._commands.leaves_on_request())

    def installed_casks(self) -> set[str]:
        return self._lines(self._commands.list_casks())

    def installed_taps(self) -> set[str]:
        return self._lines(self._commands.list_taps())

    def install_formulae(self, pkgs: set[str]) -> None:
        if pkgs:
            self._run(self._commands.install_formulae(pkgs))

    def install_casks(self, pkgs: set[str]) -> None:
        if pkgs:
            self._run(self._commands.install_casks(pkgs))

    def uninstall_formulae(self, pkgs: set[str]) -> None:
        if pkgs:
            self._run(self._commands.uninstall_formulae(pkgs))

    def uninstall_casks(self, pkgs: set[str]) -> None:
        if pkgs:
            self._run(self._commands.uninstall_casks(pkgs))

    def autoremove(self) -> None:
        self._run(self._commands.autoremove())

    def upgrade(self) -> None:
        self._run(self._commands.upgrade())

    def tap(self, taps: set[str]) -> None:
        for t in sorted(taps):
            self._run(self._commands.tap(t))

    def untap(self, taps: set[str]) -> None:
        for t in sorted(taps):
            self._run(self._commands.untap(t))


# Singleton instance. Register it (see the module docstring).
plugin: Homebrew = Homebrew()
