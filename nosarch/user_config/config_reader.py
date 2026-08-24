import json
import os
from pathlib import Path
from typing import Any

# TODO: A lot of `Any` types

_data: dict[str, Any] = {}


def _default_config_path() -> Path:
    sudo_user: str | None = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        home: str = os.path.expanduser(f"~{sudo_user}")
    else:
        home = os.path.expanduser("~")
    return Path(home) / ".nosarch_config.json"


def load() -> None:
    global _data
    config_path: Path = _default_config_path()

    if not config_path.exists():
        _data = {}
        return

    with config_path.open("r", encoding="utf-8") as file:
        _data = json.load(file)


def save() -> None:
    config_path: Path = _default_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(_data, file, indent=2)
        _ = file.write("\n")


def _get(property: str) -> Any:
    current: Any = _data

    for key in property.split("."):
        if not isinstance(current, dict) or key not in current:
            return None

        current = current[key]

    return current


def get_str(property: str, default: str = "") -> str:
    value = _get(property)

    if value is None:
        return default

    if not isinstance(value, str):
        raise TypeError(f"Expected str at '{property}', got {type(value).__name__}")

    return value


def get_bool(property: str, default: bool = False) -> bool:
    value = _get(property)

    if value is None:
        return default

    if not isinstance(value, bool):
        raise TypeError(f"Expected bool at '{property}', got {type(value).__name__}")

    return value


def get_int(property: str, default: int = 0) -> int:
    value = _get(property)

    if value is None:
        return default

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"Expected int at '{property}', got {type(value).__name__}")

    return value


def get_str_list(property: str, default: list[str] | None = None) -> list[str]:
    value = _get(property)

    if value is None:
        return [] if default is None else default

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"Expected list[str] at '{property}'")

    return value


def set_value(property: str, value: Any) -> None:
    keys: list[str] = property.split(".")
    current: dict[str, Any] = _data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}

        child = current[key]

        if not isinstance(child, dict):
            raise TypeError(f"Cannot descend into '{key}': expected dict, got {type(child).__name__}")

        current = child

    current[keys[-1]] = value
