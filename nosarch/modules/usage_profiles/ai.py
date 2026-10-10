from typing import override

import decman
import utils.custom_packages
import utils.paths
from decman import File
from decman.plugins import aur, pacman
from utils.user_config_reader import UserConfigReader


class AIModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="ai_profile")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")
        self._agents: list[str] = self._user_config.get_str_list("ai.agents")
        self._apps: list[str] = self._user_config.get_str_list("ai.apps")
        self._control_planes: list[str] = self._user_config.get_str_list("ai.control-planes")

        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/ai-root", self._username
        )

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%USER%": self._username}

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        if "t3code-desktop" in self._control_planes:
            files.update(
                self._userhome_dotfiles.files(
                    "/.config/hypr/app-permissions/t3code.lua", "/.config/hypr/binds/t3code.lua"
                )
            )

        return files

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        pkgs: set[str] = set()

        # Agents
        if self._agents.__contains__("codex"):
            pkgs.add("openai-codex")

        if self._agents.__contains__("opencode"):
            pkgs.add("opencode")

        if "gemini-cli" in self._agents:
            pkgs.add("gemini-cli")

        return pkgs

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        aur_pkgs: set[str] = set()

        # Agents
        if self._agents.__contains__("kilocode"):
            aur_pkgs.add("kilo-bin")

        # Apps
        if "chatgpt-desktop" in self._apps:
            aur_pkgs.add("chatgpt-desktop")

        if "claude-desktop" in self._apps:
            aur_pkgs.add("claude-desktop")

        if "devin-desktop" in self._apps:
            aur_pkgs.add("devin-desktop")

        # Control planes
        if "t3code-desktop" in self._control_planes:
            aur_pkgs.add("t3code-bin")

        return aur_pkgs

    @aur.custom_packages  # pyright: ignore[reportUnknownMemberType]
    def custom_pkgs(self) -> set[aur.CustomPackage]:
        custom_pkgs: set[aur.CustomPackage] = set()

        # Agents
        if "antigravity-cli" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("antigravity-cli-nosarch"))

        if "claude-code" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("claude-code-nosarch"))

        if "copilot-cli" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("github-copilot-cli-nosarch"))

        if "cursor-cli" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("cursor-cli-nosarch"))

        if "grok-build" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("grok-build-nosarch"))

        if "devin-cli" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("devin-cli-nosarch"))

        if "pi" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("pi-nosarch"))

        if "crush" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("crush-nosarch"))

        if "omp" in self._agents:
            custom_pkgs.add(utils.custom_packages.package("omp-nosarch"))

        # Apps
        if "cursor-desktop" in self._apps:
            custom_pkgs.add(utils.custom_packages.package("cursor-desktop-nosarch"))

        if "opencode-desktop" in self._apps:
            custom_pkgs.add(utils.custom_packages.package("opencode-desktop-nosarch"))

        if "github-copilot-app" in self._apps:
            custom_pkgs.add(utils.custom_packages.package("github-copilot-app-nosarch"))

        # Control planes
        if "openchamber" in self._control_planes:
            custom_pkgs.add(utils.custom_packages.package("openchamber-nosarch"))

        if "t3code-cli" in self._control_planes:
            custom_pkgs.add(utils.custom_packages.package("t3code-cli-nosarch"))

        if "zeron" in self._control_planes:
            custom_pkgs.add(utils.custom_packages.package("zeron-nosarch"))

        return custom_pkgs


# For reference
# Agents:
# - antigravity-cli -> aur.custom_packages
# - claude-code -> homebrew.casks
# - codex -> pacman.packages
# - copilot-cli -> homebrew.formulae
# - crush -> aur.custom_packages
# - cursor-cli -> aur.custom_packages
# - devin-cli -> aur.custom_packages
# - gemini-cli -> pacman.packages
# - grok-build -> aur.custom_packages
# - kilocode -> aur.packages
# - omp -> aur.custom_packages
# - opencode -> pacman.packages
# - pi -> aur.custom_packages
#
# Apps:
# - chatgpt-desktop -> aur.packages
# - claude-desktop -> aur.packages
# - cursor-desktop -> aur.custom_packages
# - devin-desktop -> aur.packages
# - github-copilot-app -> aur.custom_packages
# - opencode-desktop -> aur.custom_packages
#
# Control planes:
# - openchamber -> aur.custom_packages
# - t3code-cli -> aur.custom_packages
# - t3code-desktop -> aur.packages
# - zeron -> aur.custom_packages
