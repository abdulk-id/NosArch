"""Write `config.schema.json` from the data classes in `nosarch/user_config.py`.

Run this file after changing a setting:

    python utils/config_schema_generator.py
"""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import Any, get_origin, get_type_hints

_NOSARCH = Path(__file__).resolve().parents[1] / "nosarch"
if str(_NOSARCH) not in sys.path:
    sys.path.insert(0, str(_NOSARCH))

from user_config import Option, UserConfigReader, field_json_name  # noqa: E402

_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_ID = "https://raw.githubusercontent.com/abdulk-id/NosArch/master/config.schema.json"
_SCHEMA_TITLE = "NosArch Config"
_NO_DEFAULT = object()


def config_schema() -> dict[str, Any]:
    """The JSON schema described by ``UserConfigReader``."""
    body = object_schema(UserConfigReader)
    schema: dict[str, Any] = {"$schema": _SCHEMA_DIALECT, "$id": _SCHEMA_ID, "title": _SCHEMA_TITLE}
    if "description" in body:
        schema["description"] = body["description"]
    schema["type"] = body["type"]
    schema["properties"] = body["properties"]
    if "required" in body:
        schema["required"] = body["required"]
    return schema


def config_schema_text() -> str:
    return _json_text(config_schema()) + "\n"


def object_schema(cls: type[Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    hints = get_type_hints(cls)

    for config_field in fields(cls):
        if config_field.metadata.get("skip"):
            continue
        key = field_json_name(config_field)
        properties[key] = _field_schema(config_field, hints[config_field.name])
        if config_field.default is MISSING and config_field.default_factory is MISSING:
            required.append(key)

    body: dict[str, Any] = {"properties": properties}
    if required:
        body["required"] = required
    return _compose("object", _class_description(cls), body, _NO_DEFAULT)


def schema_file_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.schema.json"


def _field_schema(config_field: Any, hint: Any) -> dict[str, Any]:
    description = config_field.metadata.get("description")
    if not isinstance(description, str):
        description = None

    if isinstance(hint, type) and is_dataclass(hint):
        return object_schema(hint)

    if hint is bool or hint is str:
        type_name = "boolean" if hint is bool else "string"
        return _compose(type_name, description, {}, _schema_default(config_field, hint))

    origin = get_origin(hint)
    if origin is list:
        body = {"items": _items_schema(config_field.metadata.get("choices")), "uniqueItems": True}
        return _compose("array", description, body, _schema_default(config_field, hint))

    if origin is dict:
        body = {"additionalProperties": {"type": "string"}, "propertyNames": {"type": "string"}}
        return _compose("object", description, body, _schema_default(config_field, hint))

    raise TypeError(f"Unsupported config field '{config_field.name}'")


def _items_schema(choices: tuple[str | Option, ...] | None) -> dict[str, Any]:
    if not choices:
        return {"type": "string"}

    if all(isinstance(choice, str) for choice in choices):
        return {"type": "string", "enum": list(choices)}

    options: list[dict[str, str]] = []
    for choice in choices:
        if isinstance(choice, str):
            raise TypeError("Mixed choice kinds are not supported")
        option = {"const": choice.value, "title": choice.title}
        if choice.description:
            option["description"] = choice.description
        options.append(option)
    return {"type": "string", "anyOf": options}


def _schema_default(config_field: Any, hint: Any) -> Any:
    if is_dataclass(hint):
        return _NO_DEFAULT
    if config_field.default is not MISSING:
        return config_field.default
    if config_field.default_factory is not MISSING:
        return config_field.default_factory()
    return _NO_DEFAULT


def _class_description(cls: type[Any]) -> str | None:
    # A dataclass with no description gets an automatic summary of its fields. That is not a config description.
    doc = inspect.getdoc(cls)
    if doc is None or doc.startswith(f"{cls.__name__}("):
        return None
    return doc


def _json_text(value: Any, indent: int = 4, level: int = 0) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        compact = _compact_dict(value)
        if compact is not None and len(compact) <= 88:
            return compact
        pad = " " * (indent * (level + 1))
        closing = " " * (indent * level)
        lines = [f"{pad}{json.dumps(key)}: {_json_text(item, indent, level + 1)}" for key, item in value.items()]
        return "{\n" + ",\n".join(lines) + "\n" + closing + "}"

    if isinstance(value, list):
        if not value:
            return "[]"
        compact = _compact_list(value)
        if compact is not None and len(compact) <= 88:
            return compact
        pad = " " * (indent * (level + 1))
        closing = " " * (indent * level)
        lines = [pad + _json_text(item, indent, level + 1) for item in value]
        return "[\n" + ",\n".join(lines) + "\n" + closing + "]"

    return json.dumps(value)


def _compact_dict(value: dict[str, Any]) -> str | None:
    # Choice entries without a description stay on one line. Everything else stays expanded.
    if "const" not in value or "description" in value:
        return None
    if any(isinstance(item, dict | list) for item in value.values()):
        return None
    parts = [f"{json.dumps(key)}: {json.dumps(item)}" for key, item in value.items()]
    return "{ " + ", ".join(parts) + " }"


def _compact_list(value: list[Any]) -> str | None:
    if any(isinstance(item, dict | list) for item in value):
        return None
    return "[" + ", ".join(json.dumps(item) for item in value) + "]"


def _compose(type_name: str, description: str | None, body: dict[str, Any], default: Any) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": type_name}
    if description:
        schema["description"] = description
    schema.update(body)
    if default is not _NO_DEFAULT:
        schema["default"] = default
    return schema


if __name__ == "__main__":
    schema_file_path().write_text(config_schema_text(), encoding="utf-8")
