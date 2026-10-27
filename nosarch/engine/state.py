"""What the engine remembers between runs."""

import json
import os
import pwd
import tempfile
from dataclasses import dataclass, field
from typing import Any

import engine.changes
import engine.module
import engine.output

# World-readable on purpose: a dry run reads it without root. It holds paths, package names, and unit names, nothing
# that is not already readable elsewhere on the system.
STATE_FILE: str = "/var/lib/nosarch/state.json"
STATE_VERSION: int = 1

DECMAN_STORE: str = "/var/lib/decman/store.json"

# decman's per-module store keys, by the kind they hold.
_DECMAN_KIND_KEYS: dict[str, str] = {
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
    "snap": "snaps_for_module",
    "snap_classic": "classic_snaps_for_module",
}

# Files decman managed are not attributed to a module, since decman kept one list. Files no module declares any more
# are removed under this name, so they are removed but no module's hook hears about it.
IMPORTED_FILES_OWNER: str = "(decman)"


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


def _decode_decman_sets(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__type__") == "set" and "items" in value:
        return set(value["items"])
    return value


def _decman_custom_package_name(entry: str) -> str:
    """decman stored custom packages as `CustomPackage(pkgname=<name>, pkgbuild_directory=...)`."""

    prefix: str = "CustomPackage(pkgname="
    if entry.startswith(prefix):
        return entry.removeprefix(prefix).split(",", 1)[0]
    return entry


def decman_store_exists() -> bool:
    return os.path.exists(DECMAN_STORE)


def import_decman_store() -> State:
    """
    Builds the state from decman's store, so the first run after switching does not treat everything as new.

    Without it, every module would look newly enabled and every hook would fire, files decman deployed but no module
    declares any more would never be removed, and units decman enabled would never be disabled.
    """

    with open(DECMAN_STORE, "r", encoding="utf-8") as file:
        store: dict[str, Any] = json.load(file, object_hook=_decode_decman_sets)

    state: State = State()

    # decman's own user manager was a module. Users are a built-in step now.
    state.enabled_modules = [name for name in store.get("enabled_modules", []) if name != "usermanager"]

    state.files = {IMPORTED_FILES_OWNER: sorted(store.get("all_files", []))}

    for kind, key in _DECMAN_KIND_KEYS.items():
        for module, value in store.get(key, {}).items():
            if module == "usermanager":
                continue
            # Snaps were stored as {name: channel}, user kinds as {user: {names}}, the rest as sets of names.
            if kind in engine.module.USER_KINDS:
                identities: set[str] = engine.module.identities(kind, value)
            elif kind == "custom":
                identities = {_decman_custom_package_name(entry) for entry in value}
            else:
                identities = set(value)
            state.declared.setdefault(module, {})[kind] = sorted(identities)

    state.systemd_units = sorted(store.get("systemd_units", set()))
    state.systemd_user_units = {user: sorted(units) for user, units in store.get("systemd_user_units", {}).items()}

    # decman recorded every user it was told about, including accounts that existed before it. Only system accounts
    # are taken as created by it, so a renamed login user is never deleted.
    for user in store.get("usermanager_users", set()):
        try:
            if pwd.getpwnam(user).pw_uid < 1000:
                state.created_users.append(user)
        except KeyError:
            continue

    state.aur_reviewed = dict(store.get("pkgbuild_latest_reviewed_commits", {}))

    engine.output.print_info(f"Imported decman's state from {DECMAN_STORE}.")
    return state
