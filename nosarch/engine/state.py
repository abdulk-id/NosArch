import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

import engine.changes

STATE_FILE: str = "/var/lib/nosarch/state.json"
STATE_VERSION: int = 1


@dataclass
class State:
    enabled_modules: list[str] = field(default_factory=list)
    files: dict[str, list[str]] = field(default_factory=dict)
    declared: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    systemd_units: list[str] = field(default_factory=list)
    systemd_user_units: dict[str, list[str]] = field(default_factory=dict)
    created_users: list[str] = field(default_factory=list)
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
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return State.from_json(json.load(file))
    except FileNotFoundError:
        return None
