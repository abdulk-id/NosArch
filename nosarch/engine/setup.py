"""What the definition code hands the engine, and what the steps share during a run."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import engine.changes
import engine.module
import engine.state


@dataclass(frozen=True)
class User:
    """
    An account the users step makes sure exists.

    `groups` is the complete list of supplementary groups: the user is added to the missing ones and removed from any
    other. `system` only matters when the account is created.
    """

    username: str
    group: str | None = None
    home: str | None = None
    shell: str | None = None
    groups: tuple[str, ...] = ()
    system: bool = False


@dataclass
class AurSettings:
    # Builds run as this user, never as root. makepkg refuses root, and a build script should not get it anyway.
    build_user: str = "nobody"
    # Build in a fresh chroot, so the host's installed packages cannot leak into a build. Without it, makepkg runs on
    # the host, and build dependencies are installed there for the build and removed after.
    clean_chroot: bool = True
    build_dir: str = "/var/cache/nosarch/build"
    # Built packages are kept here. In a chroot build, an AUR dependency has to be handed over as a package file, so
    # keeping them saves rebuilding a dependency that has not changed.
    package_cache_dir: str = "/var/cache/nosarch/packages"
    # Foreign packages the engine neither installs, upgrades, nor removes.
    ignored: set[str] = field(default_factory=set)
    # Maps a custom package's name to the directory holding its PKGBUILD, or None when there is none. The flag says
    # whether it may fetch first; a dry run passes False, since fetching writes to a root-owned cache.
    custom_pkgbuild_dir: Callable[[str, bool], str | None] | None = None
    # Rebuild VCS packages (-git and the like) even when the AUR version has not moved. Set by `--aur-upgrade-devel`.
    upgrade_devel: bool = False


@dataclass
class Setup:
    """Everything the definition code declares, built by `source.setup()`."""

    # Registration order is hook order within a phase.
    modules: list[engine.module.Module] = field(default_factory=list)
    # Modules the definition code knows about but did not enable. Only their `on_disable` is ever called.
    disabled_modules: list[engine.module.Module] = field(default_factory=list)
    users: list[User] = field(default_factory=list)
    steps: list[str] = field(default_factory=lambda: ["users", "files", "pacman", "aur", "systemd"])
    aur: AurSettings = field(default_factory=AurSettings)
    # brew refuses to run as root, so every brew command runs as this user.
    homebrew_user: str | None = None

    def add(self, module: engine.module.Module, enabled: bool = True) -> None:
        if enabled:
            self.modules.append(module)
        else:
            self.disabled_modules.append(module)


@dataclass
class Context:
    """One run: the setup, the saved state, and what the steps found."""

    setup: Setup
    state: engine.state.State
    dry_run: bool
    # Each enabled module's declarations, by kind. See `engine.module.declarations`.
    declarations: dict[str, dict[str, Any]] = field(default_factory=dict)
    # What changed for each module this run.
    changes: dict[str, engine.changes.Changes] = field(default_factory=dict)

    def changes_for(self, module: str) -> engine.changes.Changes:
        return self.changes.setdefault(module, engine.changes.Changes())

    def declared(self, kind: str) -> Any:
        """Every enabled module's declarations of `kind`, merged."""

        if kind in engine.module.USER_KINDS:
            merged_users: dict[str, set[str]] = {}
            for declarations in self.declarations.values():
                for user, names in declarations[kind].items():
                    merged_users.setdefault(user, set()).update(names)
            return merged_users

        if kind in engine.module.DETAIL_KINDS:
            merged_details: dict[str, str] = {}
            for declarations in self.declarations.values():
                merged_details.update(declarations[kind])
            return merged_details

        merged: set[str] = set()
        for declarations in self.declarations.values():
            merged |= declarations[kind]
        return merged
