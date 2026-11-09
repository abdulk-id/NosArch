from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import engine.changes
import engine.module
import engine.state


@dataclass(frozen=True)
class User:
    """An account. groups is the full supplementary list; system matters only when the account is created."""

    username: str
    group: str | None = None
    home: str | None = None
    shell: str | None = None
    groups: tuple[str, ...] = ()
    system: bool = False


@dataclass
class AurSettings:
    build_user: str = "nobody"
    clean_chroot: bool = True
    build_dir: str = "/var/cache/nosarch/build"
    package_cache_dir: str = "/var/cache/nosarch/packages"
    ignored: set[str] = field(default_factory=set)
    custom_pkgbuild_dir: Callable[[str, bool], str | None] | None = None
    upgrade_devel: bool = False


@dataclass
class Setup:
    """Everything the definition code declares."""

    modules: list[engine.module.Module] = field(default_factory=list)
    disabled_modules: list[engine.module.Module] = field(default_factory=list)
    users: list[User] = field(default_factory=list)
    steps: list[str] = field(default_factory=lambda: ["users", "files", "pacman", "aur", "systemd"])
    aur: AurSettings = field(default_factory=AurSettings)
    homebrew_user: str | None = None

    def add(self, module: engine.module.Module, enabled: bool = True) -> None:
        if enabled:
            self.modules.append(module)
        else:
            self.disabled_modules.append(module)


@dataclass
class Context:
    setup: Setup
    state: engine.state.State
    dry_run: bool
    declarations: dict[str, dict[str, Any]] = field(default_factory=dict)
    changes: dict[str, engine.changes.Changes] = field(default_factory=dict)

    def changes_for(self, module: str) -> engine.changes.Changes:
        return self.changes.setdefault(module, engine.changes.Changes())

    def declared(self, kind: str) -> Any:
        return engine.module.collect(kind, self.declarations)
