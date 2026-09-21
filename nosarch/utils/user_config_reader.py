import json
import os
from pathlib import Path
from typing import Any

# TODO: A lot of `Any` types


class UserConfigReader:
    def __init__(self) -> None:
        self._config_file_path: Path = self._default_config_path()
        self._data: dict[str, Any] = self._load_config()
        pass

    def _default_config_path(self) -> Path:
        sudo_user: str | None = os.environ.get("SUDO_USER")
        if sudo_user and sudo_user != "root":
            home: str = os.path.expanduser(f"~{sudo_user}")
        else:
            home = os.path.expanduser("~")
        return Path(home) / ".nosarch_config.json"

    def _load_config(self) -> Any:
        if not self._config_file_path.exists():
            return

        with self._config_file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self) -> None:
        self._config_file_path.parent.mkdir(parents=True, exist_ok=True)

        with self._config_file_path.open("w", encoding="utf-8") as file:
            json.dump(self._data, file, indent=2)
            _ = file.write("\n")

    def _get(self, property: str) -> Any:
        current = self._data

        for key in property.split("."):
            if not isinstance(current, dict) or key not in current:
                return None

            current = current[key]

        return current

    def get_str(self, property: str, default: str = "") -> str:
        value = self._get(property)

        if value is None:
            return default

        if not isinstance(value, str):
            raise TypeError(f"Expected str at '{property}', got {type(value).__name__}")

        return value

    def get_bool(self, property: str, default: bool = False) -> bool:
        value = self._get(property)

        if value is None:
            return default

        if not isinstance(value, bool):
            raise TypeError(f"Expected bool at '{property}', got {type(value).__name__}")

        return value

    def get_int(self, property: str, default: int = 0) -> int:
        value = self._get(property)

        if value is None:
            return default

        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"Expected int at '{property}', got {type(value).__name__}")

        return value

    def get_str_list(self, property: str, default: list[str] | None = None) -> list[str]:
        value = self._get(property)

        if value is None:
            return [] if default is None else default

        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise TypeError(f"Expected list[str] at '{property}'")

        return value

    def set_value(self, property: str, value: Any) -> None:
        keys: list[str] = property.split(".")
        current: dict[str, Any] = self._data

        for key in keys[:-1]:
            if key not in self._data:
                current[key] = {}

            child = current[key]

            if not isinstance(child, dict):
                raise TypeError(f"Cannot descend into '{key}': expected dict, got {type(child).__name__}")

            current = child

        current[keys[-1]] = value
