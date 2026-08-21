from abc import ABC, abstractmethod
from typing import override

from config import DEV_LANGS_ENABLED


class DevLang(ABC):
    @abstractmethod
    def get_tools_config(self) -> str:
        pass

    @abstractmethod
    def get_settings_config(self) -> str:
        pass


# Language config classes


class BunJSConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'bun = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class DenoJSConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'deno = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class GoConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'go = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class JavaMavenConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'java = "temurin"\nmaven = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class JavaGradleConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'java = "temurin"\ngradle = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class DotNetConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'dotnet = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class NodeJSConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'node = "lts"\nnpm = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class PythonConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'python = "latest"\nuv = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


class RustConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'rust = { version = "stable", components = "rustfmt,clippy" }'

    @override
    def get_settings_config(self) -> str:
        return ""


class ZigConfig(DevLang):
    @override
    def get_tools_config(self) -> str:
        return 'zig = "latest"\nzls = "latest"'

    @override
    def get_settings_config(self) -> str:
        return ""


# Main logic

DEV_LANG_CONFIG: dict[str, DevLang] = {
    "denojs": DenoJSConfig(),
    "bunjs": BunJSConfig(),
    "go": GoConfig(),
    "java_maven": JavaMavenConfig(),
    "java_gradle": JavaGradleConfig(),
    ".net": DotNetConfig(),
    "nodejs": NodeJSConfig(),
    "python": PythonConfig(),
    "rust": RustConfig(),
    "zig": ZigConfig(),
}


def get_mise_config_contents() -> str:
    config_contents: list[str] = []

    # Mise tools
    config_contents.append("[tools]\n")

    for lang, enabled in DEV_LANGS_ENABLED.items():
        if enabled:
            if DEV_LANG_CONFIG[lang].get_tools_config() != "":
                config_contents.append(DEV_LANG_CONFIG[lang].get_tools_config())
                config_contents.append("\n")

    # Mise settings
    config_contents.append("\n")
    config_contents.append("[settings]\n")
    config_contents.append("activate_aggressive = true\n")
    config_contents.append("paranoid = false\n")
    config_contents.append("terminal_progress = true\n")

    for lang, enabled in DEV_LANGS_ENABLED.items():
        if enabled:
            if DEV_LANG_CONFIG[lang].get_settings_config() != "":
                config_contents.append(DEV_LANG_CONFIG[lang].get_settings_config())
                config_contents.append("\n")

    return "".join(config_contents)
