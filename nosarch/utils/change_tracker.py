from typing import override

from decman import Directory, File, Symlink


class ChangeTracker:
    """Collects the paths decman actually wrote during this run."""

    def __init__(self) -> None:
        self.changed: set[str] = set()

    def changed_under(self, *prefixes: str) -> bool:
        return any(p.startswith(prefix) for p in self.changed for prefix in prefixes)

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
            self._tracker.changed.add(target)
        return changed


class _TrackedDirectory(Directory):
    def __init__(self, tracker: ChangeTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker: ChangeTracker = tracker

    @override
    def copy_to(self, target_directory, variables=None, dry_run=False) -> tuple[list[str], list[str]]:
        checked, changed = super().copy_to(target_directory, variables, dry_run)
        if not dry_run:
            self._tracker.changed.update(changed)
        return checked, changed


class _TrackedSymlink(Symlink):
    def __init__(self, tracker: ChangeTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker: ChangeTracker = tracker

    @override
    def link_to(self, link_name, dry_run=False) -> bool:
        changed: bool = super().link_to(link_name, dry_run)
        if changed and not dry_run:
            self._tracker.changed.add(link_name)
        return changed
