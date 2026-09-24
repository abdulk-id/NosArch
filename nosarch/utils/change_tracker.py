import copy
import os
from typing import Any, override

from decman import Directory, File, Store, Symlink

# Store keys decman's plugins (and NosArch's homebrew plugin) keep per module.
_PACKAGE_STORE_KEYS: dict[str, str] = {
    "pacman": "packages_for_module",
    "aur": "aur_packages_for_module",
    "custom": "custom_packages_for_module",
    "flatpak": "flatpaks_for_module",
    "flatpak_user": "user_flatpaks_for_module",
    "systemd": "systemd_units_for_module",
    "systemd_user": "systemd_user_units_for_module",
    "brew_formula": "brew_formulae_for_module",
    "brew_cask": "brew_casks_for_module",
    "brew_tap": "brew_taps_for_module",
}


def _flatten(value: Any) -> set[str]:
    # User-scoped kinds are stored as {user: {names}}.
    if isinstance(value, dict):
        return {f"{user}:{name}" for user, names in value.items() for name in names}
    return set(value or ())


class ChangeTracker:
    """Collects the file paths decman wrote to, and the packages and units it added or removed during this run."""

    def __init__(self) -> None:
        self.changed_files: set[str] = set()
        self.added_pkgs: dict[str, set[str]] = {kind: set() for kind in _PACKAGE_STORE_KEYS}
        self.removed_pkgs: dict[str, set[str]] = {kind: set() for kind in _PACKAGE_STORE_KEYS}
        self._previous_pkgs: dict[str, Any] = {}

    def changed_files_under(self, *target_dirs: str) -> bool:
        for target_dir in target_dirs:
            target: str = os.path.abspath(target_dir)
            if any(os.path.commonpath([p, target]) == target for p in self.changed_files):
                return True
        return False

    def snapshot_packages(self, store: Store, module_name: str) -> None:
        """Call from `before_update`, before the plugins overwrite last run's entries."""
        self._previous_pkgs = {
            kind: copy.deepcopy(store.get(key, {}).get(module_name)) for kind, key in _PACKAGE_STORE_KEYS.items()
        }

    def diff_packages(self, store: Store, module_name: str) -> None:
        """Call from `on_change`, after the plugins have written this run's entries."""
        for kind, key in _PACKAGE_STORE_KEYS.items():
            before: set[str] = _flatten(self._previous_pkgs.get(kind))
            after: set[str] = _flatten(store.get(key, {}).get(module_name))
            self.added_pkgs[kind] = after - before
            self.removed_pkgs[kind] = before - after

    def package_changed(self, *names: str, kinds: tuple[str, ...] | None = None) -> bool:
        for kind in kinds or tuple(_PACKAGE_STORE_KEYS):
            if not (self.added_pkgs[kind] | self.removed_pkgs[kind]).isdisjoint(names):
                return True
        return False

    # Factories, so modules read almost the same as before.
    def file(self, **kwargs) -> File:
        return _TrackedFile(self, **kwargs)

    def directory(self, **kwargs) -> Directory:
        return _TrackedDirectory(self, **kwargs)

    def symlink(self, **kwargs) -> Symlink:
        return _TrackedSymlink(self, **kwargs)


class _TrackedFile(File):
    def __init__(self, tracker: ChangeTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker: ChangeTracker = tracker

    @override
    def copy_to(self, target, variables=None, dry_run=False) -> bool:
        changed: bool = super().copy_to(target, variables, dry_run)
        if changed and not dry_run:
            self._tracker.changed_files.add(target)
        return changed


class _TrackedDirectory(Directory):
    def __init__(self, tracker: ChangeTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker: ChangeTracker = tracker

    @override
    def copy_to(self, target_directory, variables=None, dry_run=False) -> tuple[list[str], list[str]]:
        checked, changed = super().copy_to(target_directory, variables, dry_run)
        if not dry_run:
            self._tracker.changed_files.update(changed)
        return checked, changed


class _TrackedSymlink(Symlink):
    def __init__(self, tracker: ChangeTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker: ChangeTracker = tracker

    @override
    def link_to(self, link_name, dry_run=False) -> bool:
        changed: bool = super().link_to(link_name, dry_run)
        if changed and not dry_run:
            self._tracker.changed_files.add(link_name)
        return changed
