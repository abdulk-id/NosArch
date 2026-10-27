from typing import override

import engine
import utils.apply
import utils.custom_packages
import utils.paths
from engine import File
from engine.steps import aur, pacman
from user_config import UserConfigReader


class AISetupModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="ai_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username
        self._agents: list[str] = self._user_config.setups.ai.agents
        self._apps: list[str] = self._user_config.setups.ai.apps
        self._control_planes: list[str] = self._user_config.setups.ai.control_planes

        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/ai-setup-root", self._username
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

    @override
    def on_change(self, changes: engine.Changes) -> None:
        if changes.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            utils.apply.reload_hyprland()

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

        # Control planes
        if "t3code-desktop" in self._control_planes:
            aur_pkgs.add("t3code-nightly-bin")

        return aur_pkgs

    @aur.custom_packages  # pyright: ignore[reportUnknownMemberType]
    def custom_pkgs(self) -> set[str]:
        custom_pkgs: set[str] = set()

        # Agents
        if "antigravity-cli" in self._agents:
            custom_pkgs.add("antigravity-cli-nosarch")

        if "claude-code" in self._agents:
            custom_pkgs.add("claude-code-nosarch")

        if "copilot-cli" in self._agents:
            custom_pkgs.add("github-copilot-cli-nosarch")

        if "cursor-cli" in self._agents:
            custom_pkgs.add("cursor-cli-nosarch")

        if "grok-build" in self._agents:
            custom_pkgs.add("grok-build-nosarch")

        if "devin-cli" in self._agents:
            custom_pkgs.add("devin-cli-nosarch")

        if "pi" in self._agents:
            custom_pkgs.add("pi-nosarch")

        if "crush" in self._agents:
            custom_pkgs.add("crush-nosarch")

        if "omp" in self._agents:
            custom_pkgs.add("omp-nosarch")

        if "mimocode" in self._agents:
            custom_pkgs.add("mimocode-nosarch")

        if "muse-code" in self._agents:
            custom_pkgs.add("muse-code-nosarch")

        # Apps
        if "chatgpt-desktop" in self._apps:
            custom_pkgs.add("chatgpt-desktop-nosarch")

        if "claude-desktop" in self._apps:
            custom_pkgs.add("claude-desktop-nosarch")

        if "cursor-desktop" in self._apps:
            custom_pkgs.add("cursor-desktop-nosarch")

        if "devin-desktop" in self._apps:
            custom_pkgs.add("devin-desktop-nosarch")

        if "opencode-desktop" in self._apps:
            custom_pkgs.add("opencode-desktop-nosarch")

        if "github-copilot-app" in self._apps:
            custom_pkgs.add("github-copilot-app-nosarch")

        # Control planes
        if "openchamber" in self._control_planes:
            custom_pkgs.add("openchamber-nosarch")

        if "t3code-cli" in self._control_planes:
            custom_pkgs.add("t3code-cli-nosarch")

        if "zeron" in self._control_planes:
            custom_pkgs.add("zeron-nosarch")

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
# - muse-code -> aur.custom_packages
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
