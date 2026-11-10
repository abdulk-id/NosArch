import os
from typing import Any

KINDS: tuple[str, ...] = (
    "pacman",
    "aur",
    "custom",
    "systemd",
    "systemd_user",
    "flatpak",
    "flatpak_user",
    "brew_formula",
    "brew_cask",
    "brew_tap",
    "snap",
    "snap_classic",
)


class Changes:
    def __init__(self) -> None:
        self.changed_files: set[str] = set()
        self.added_pkgs: dict[str, set[str]] = {kind: set() for kind in KINDS}
        self.removed_pkgs: dict[str, set[str]] = {kind: set() for kind in KINDS}

    def __bool__(self) -> bool:
        return bool(self.changed_files) or any(self.added_pkgs.values()) or any(self.removed_pkgs.values())

    def files_changed(self, *paths: str) -> bool:
        return not self.changed_files.isdisjoint(paths)

    def files_changed_in_dirs(self, *target_dirs: str) -> bool:
        """Whether a changed path is inside one of target_dirs, compared by path components."""

        for target_dir in target_dirs:
            target: str = os.path.abspath(target_dir)
            if any(os.path.commonpath([path, target]) == target for path in self.changed_files):
                return True
        return False

    def package_changed(self, *names: str, kinds: tuple[str, ...] | None = None) -> bool:
        return any(not (self.added_pkgs[kind] | self.removed_pkgs[kind]).isdisjoint(names) for kind in (kinds or KINDS))

    def merge(self, other: "Changes") -> None:
        self.changed_files |= other.changed_files
        for kind in KINDS:
            self.added_pkgs[kind] |= other.added_pkgs[kind]
            self.removed_pkgs[kind] |= other.removed_pkgs[kind]

    def summary(self) -> list[str]:
        lines: list[str] = []
        if self.changed_files:
            lines.append(f"files: {', '.join(sorted(self.changed_files))}")
        for kind in KINDS:
            if self.added_pkgs[kind]:
                lines.append(f"{kind} added: {', '.join(sorted(self.added_pkgs[kind]))}")
            if self.removed_pkgs[kind]:
                lines.append(f"{kind} removed: {', '.join(sorted(self.removed_pkgs[kind]))}")
        return lines

    def to_json(self) -> dict[str, Any]:
        return {
            "files": sorted(self.changed_files),
            "added": {kind: sorted(names) for kind, names in self.added_pkgs.items() if names},
            "removed": {kind: sorted(names) for kind, names in self.removed_pkgs.items() if names},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Changes":
        changes: Changes = cls()
        changes.changed_files = set(data.get("files", []))
        for kind in KINDS:
            changes.added_pkgs[kind] = set(data.get("added", {}).get(kind, []))
            changes.removed_pkgs[kind] = set(data.get("removed", {}).get(kind, []))
        return changes
