"""NosArch user config data classes.

These data classes are the source of truth. Each setting lives on a field, including its default and its description.
`config.schema.json` is generated from these classes by `utils/config_schema_generator.py`.
"""

from __future__ import annotations

import json
import os
from dataclasses import MISSING, Field, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, ClassVar, Protocol, TypeVar, get_origin, get_type_hints


class _ConfigClass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


_T = TypeVar("_T", bound=_ConfigClass)


class Option:
    """One allowed choice, with the label shown by editors."""

    def __init__(self, value: str, title: str, description: str = "") -> None:
        self.value: str = value
        self.title: str = title
        self.description: str = description


def text(description: str, *, default: str | None = None) -> Any:
    """A string setting. Leave the default out when the config file must include it."""
    metadata = {"description": description}
    if default is None:
        return field(metadata=metadata)
    return field(default=default, metadata=metadata)


def flag(description: str, *, default: bool = False) -> Any:
    """A yes/no setting. ``default=True`` is kept when the config file omits the setting."""
    return field(default=default, metadata={"description": description})


def text_list(
    description: str, *, json_name: str | None = None, choices: tuple[str | Option, ...] | None = None
) -> Any:
    """A list of strings. ``json_name`` is the config-file name when it differs from the field name."""
    metadata: dict[str, Any] = {"description": description}
    if json_name is not None:
        metadata["json_name"] = json_name
    if choices is not None:
        metadata["choices"] = choices
    return field(default_factory=list, metadata=metadata)


def text_map(description: str, *, json_name: str) -> Any:
    """A mapping of strings to strings, such as a snap name to its channel."""
    return field(default_factory=dict, metadata={"description": description, "json_name": json_name})


def field_json_name(config_field: Any) -> str:
    """The name used in the config file and the schema."""
    name = config_field.metadata.get("json_name")
    if isinstance(name, str):
        return name
    return str(config_field.name)


_AGENTS: tuple[Option, ...] = (
    Option("antigravity-cli", "Antigravity CLI"),
    Option("claude-code", "Claude Code"),
    Option("codex", "OpenAI Codex"),
    Option("copilot-cli", "GitHub Copilot CLI"),
    Option("crush", "Crush"),
    Option("cursor-cli", "Cursor CLI"),
    Option("devin-cli", "Devin CLI"),
    Option("gemini-cli", "Gemini CLI"),
    Option("grok-build", "Grok Build"),
    Option("kilocode", "Kilo Code"),
    Option("mimocode", "MiMo-Code"),
    Option("omp", "Oh My Pi"),
    Option("opencode", "OpenCode"),
    Option("pi", "Pi"),
)

_APPS: tuple[Option, ...] = (
    Option("chatgpt-desktop", "ChatGPT Desktop"),
    Option("claude-desktop", "Claude Desktop"),
    Option("cursor-desktop", "Cursor Desktop"),
    Option("devin-desktop", "Devin Desktop"),
    Option("github-copilot-app", "GitHub Copilot App"),
    Option("opencode-desktop", "OpenCode Desktop"),
)

_CONTROL_PLANES: tuple[Option, ...] = (
    Option("openchamber", "OpenChamber", "Control plane for OpenCode"),
    Option(
        "t3code-cli",
        "T3 Code (CLI & Web)",
        "Control plane for Claude Code, Codex, Cursor CLI, Grok Build, OpenCode and Antigravity",
    ),
    Option(
        "t3code-desktop",
        "T3 Code Desktop",
        "Control plane for Claude Code, Codex, Cursor CLI, Grok Build, OpenCode and Antigravity",
    ),
    Option(
        "zeron",
        "Zeron",
        "Control plane for Claude Code, Codex, Cursor CLI, Devin CLI, Grok Build, Hermes Agent, Pi, OpenCode and Antigravity",
    ),
)

_EDITORS: tuple[str, ...] = ("code-oss", "codium", "jetbrains", "neovim", "vscode", "zed")

_LANGUAGES: tuple[str, ...] = (
    ".net",
    "go",
    "java-maven",
    "java-gradle",
    "javascript-bun",
    "javascript-deno",
    "javascript-node",
    "python",
    "rust",
    "zig",
)


@dataclass
class User:
    username: str = text("User name")
    fullname: str = text("User's full name")
    git_email: str = text("User's Git email", default="")


@dataclass
class BasicSetup:
    enabled: bool = flag("Enable Basic Setup")
    enable_virtualization: bool = flag("Setup NosArch for running Virtual Machines")


@dataclass
class AiSetup:
    enabled: bool = flag("Setup NosArch for AI and Agentic work")
    agents: list[str] = text_list("List of AI agents to install", choices=_AGENTS)
    apps: list[str] = text_list("List of AI apps to install", choices=_APPS)
    control_planes: list[str] = text_list(
        "List of Agent control planes to install", json_name="control-planes", choices=_CONTROL_PLANES
    )


@dataclass
class CreativeSetup:
    enabled: bool = flag("Setup NosArch for Creative work")


@dataclass
class DevSetup:
    enabled: bool = flag("Setup NosArch for Software Development")
    editors: list[str] = text_list("List of code editors to install", choices=_EDITORS)
    languages: list[str] = text_list("List of programming languages to setup", choices=_LANGUAGES)


@dataclass
class GamingSetup:
    enabled: bool = flag("Setup NosArch for Gaming")


@dataclass
class Setups:
    basic: BasicSetup = field(default_factory=BasicSetup)
    ai: AiSetup = field(default_factory=AiSetup)
    creative: CreativeSetup = field(default_factory=CreativeSetup)
    dev: DevSetup = field(default_factory=DevSetup)
    gaming: GamingSetup = field(default_factory=GamingSetup)


@dataclass
class ArchPackages:
    install_packages: list[str] = text_list(
        "Add other Arch packages not pre-installed by NosArch", json_name="install-packages"
    )


@dataclass
class AurPackages:
    install_packages: list[str] = text_list(
        "Add other packages from the AUR not pre-installed by NosArch", json_name="install-packages"
    )


@dataclass
class FlatpakPackages:
    enabled: bool = flag("Add support for Flatpak packages to NosArch")
    install_packages: list[str] = text_list("Add Flatpak packages to install system-wide", json_name="install-packages")
    install_user_packages: list[str] = text_list(
        "Add Flatpak packages to install for your user", json_name="install-user-packages"
    )


@dataclass
class HomebrewPackages:
    enabled: bool = flag("Add support for Homebrew packages to NosArch")
    install_casks: list[str] = text_list("Add Homebrew casks to install", json_name="install-casks")
    install_formulae: list[str] = text_list("Add Homebrew formulae to install", json_name="install-formulae")


@dataclass
class SnapPackages:
    enabled: bool = flag("Add support for Snap packages to NosArch")
    install_snaps: dict[str, str] = text_map(
        "Add Snap packages to install, including the channel to install from", json_name="install-snaps"
    )
    install_classic_snaps: dict[str, str] = text_map(
        "Add Snap classic packages to install, including the channel to install from", json_name="install-classic-snaps"
    )


@dataclass
class Packaging:
    """Manage installed packages and packaging methods in NosArch"""

    arch: ArchPackages = field(default_factory=ArchPackages)
    aur: AurPackages = field(default_factory=AurPackages)
    flatpak: FlatpakPackages = field(default_factory=FlatpakPackages)
    homebrew: HomebrewPackages = field(default_factory=HomebrewPackages)
    snap: SnapPackages = field(default_factory=SnapPackages)


@dataclass
class System:
    enable_lts_kernel: bool = flag("Setup Linux LTS kernel")


@dataclass
class Advanced:
    enable_nosarch_works: bool = flag("Setup this machine for working on the NosArch codebase")
    enable_swapfile: bool = flag("Create a Btrfs swapfile and configure the kernel to hibernate to it")


@dataclass
class UserConfigReader:
    """Configuration schema for NosArch"""

    user: User
    setups: Setups = field(default_factory=Setups)
    packaging: Packaging = field(default_factory=Packaging)
    system: System = field(default_factory=System)
    advanced: Advanced = field(default_factory=Advanced)
    config_file_path: Path = field(init=False, repr=False, compare=False, metadata={"skip": True})

    @classmethod
    def load(cls, config_file_path: Path | None = None) -> UserConfigReader:
        path: Path = _default_config_path() if config_file_path is None else config_file_path
        if not path.exists():
            raise ValueError(f"Config file not found: {path}")

        with path.open("r", encoding="utf-8") as file:
            loaded: Any = json.load(file)

        if not isinstance(loaded, dict):
            raise TypeError(f"Expected object in config file {path}, got {type(loaded).__name__}")

        config = read_into(cls, loaded)
        config.config_file_path = path
        return config

    def save(self) -> None:
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
        text_value: str = json.dumps(to_json(self), indent=2) + "\n"
        self.config_file_path.write_text(text_value, encoding="utf-8")


def read_into(cls: type[_T], data: Any, prefix: str = "") -> _T:
    """Build ``cls`` from JSON. Missing settings use the field's default."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        where: str = prefix or "config"
        raise TypeError(f"Expected object at '{where}', got {type(data).__name__}")

    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    missing: list[str] = []

    for config_field in fields(cls):
        if config_field.metadata.get("skip"):
            continue

        key = field_json_name(config_field)
        path = f"{prefix}.{key}" if prefix else key
        if key not in data or data[key] is None:
            if config_field.default is MISSING and config_field.default_factory is MISSING:
                missing.append(path)
            continue

        kwargs[config_field.name] = _convert(hints[config_field.name], data[key], path, config_field)

    if missing:
        names = ", ".join(f"'{item}'" for item in missing)
        raise ValueError(f"Missing required config value {names}")

    return cls(**kwargs)


def to_json(config: Any) -> dict[str, Any]:
    """JSON for a config object, using the config-file names."""
    result: dict[str, Any] = {}

    for config_field in fields(config):
        if config_field.metadata.get("skip"):
            continue
        value = getattr(config, config_field.name)
        if is_dataclass(value):
            value = to_json(value)
        result[field_json_name(config_field)] = value

    return result


def _default_config_path() -> Path:
    sudo_user: str | None = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        home = os.path.expanduser(f"~{sudo_user}")
    else:
        home = os.path.expanduser("~")
    return Path(home) / ".nosarch_config.json"


def _convert(hint: Any, value: Any, path: str, config_field: Any) -> Any:
    if isinstance(hint, type) and is_dataclass(hint):
        return read_into(hint, value, path)

    if hint is bool:
        if type(value) is not bool:
            raise TypeError(f"Expected bool at '{path}', got {type(value).__name__}")
        return value

    if hint is str:
        if type(value) is not str:
            raise TypeError(f"Expected str at '{path}', got {type(value).__name__}")
        return value

    origin = get_origin(hint)
    if origin is list:
        if type(value) is not list or not all(type(item) is str for item in value):
            raise TypeError(f"Expected list[str] at '{path}'")
        _check_choices(value, path, config_field.metadata.get("choices"))
        return list(value)

    if origin is dict:
        if type(value) is not dict or not all(type(key) is str and type(item) is str for key, item in value.items()):
            raise TypeError(f"Expected dict[str, str] at '{path}'")
        return dict(value)

    raise TypeError(f"Unsupported config type at '{path}'")


def _check_choices(values: list[str], path: str, choices: tuple[str | Option, ...] | None) -> None:
    if not choices:
        return

    allowed: set[str] = {choice.value if isinstance(choice, Option) else choice for choice in choices}
    for value in values:
        if value not in allowed:
            raise ValueError(f"Unknown value {value!r} at '{path}'")
