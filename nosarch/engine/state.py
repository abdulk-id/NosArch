"""What the engine remembers between runs."""

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

import engine.changes

# World-readable on purpose: a dry run reads it without root. It holds paths, package names, and unit names, nothing
# that is not already readable elsewhere on the system.
STATE_FILE: str = "/var/lib/nosarch/state.json"
STATE_VERSION: int = 1


@dataclass
class State:
    enabled_modules: list[str] = field(default_factory=list)
    # Target paths deployed by each module.
    files: dict[str, list[str]] = field(default_factory=dict)
    # Each module's declarations on the last run, by kind, flattened to identities. Diffing against these is how
    # package and unit changes are found.
    declared: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    # Changes recorded but not yet seen by the module's on_change hook.
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Units the engine enabled, so it only ever disables what it enabled itself.
    systemd_units: list[str] = field(default_factory=list)
    systemd_user_units: dict[str, list[str]] = field(default_factory=dict)
    # Accounts the engine created, the only ones it would delete.
    created_users: list[str] = field(default_factory=list)
    # AUR package base to the last commit the user reviewed.
    aur_reviewed: dict[str, str] = field(default_factory=dict)

    def pending_changes(self, module: str) -> engine.changes.Changes:
        return engine.changes.Changes.from_json(self.pending.get(module, {}))

    def to_json(self) -> dict[str, Any]:
        return {
            "version": STATE_VERSION,
            "enabled_modules": self.enabled_modules,
            "files": {module: sorted(paths) for module, paths in self.files.items()},
            "declared": self.declared,
            "pending": self.pending,
            "systemd_units": sorted(self.systemd_units),
            "systemd_user_units": {user: sorted(units) for user, units in self.systemd_user_units.items()},
            "created_users": sorted(self.created_users),
            "aur_reviewed": self.aur_reviewed,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "State":
        return cls(
            enabled_modules=list(data.get("enabled_modules", [])),
            files={module: list(paths) for module, paths in data.get("files", {}).items()},
            declared=data.get("declared", {}),
            pending=data.get("pending", {}),
            systemd_units=list(data.get("systemd_units", [])),
            systemd_user_units={user: list(units) for user, units in data.get("systemd_user_units", {}).items()},
            created_users=list(data.get("created_users", [])),
            aur_reviewed=dict(data.get("aur_reviewed", {})),
        )

    def save(self) -> None:
        """Writes the state atomically, so an interrupted write leaves the previous state in place."""

        directory: str = os.path.dirname(STATE_FILE)
        os.makedirs(directory, mode=0o755, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as temporary:
            json.dump(self.to_json(), temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())

        os.chmod(temporary.name, 0o644)
        os.replace(temporary.name, STATE_FILE)


def load() -> State | None:
    """The saved state, or None when there is none yet."""

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return State.from_json(json.load(file))
    except FileNotFoundError:
        return None
