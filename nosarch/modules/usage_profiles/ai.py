import os
from typing import override

import decman
import utils.paths
from decman import File
from decman.plugins import aur, pacman
from plugins import homebrew
from utils.user_config_reader import UserConfigReader

# decman reads `source.py` as text and `exec()`s it after `os.chdir`-ing into its directory,
# so package paths are resolved relative to `nosarch/`, not to this file.
_PACKAGES_DIR: str = os.path.abspath("packages")


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
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        files.update(self._userhome_dotfiles.files("/.agents/skills/bro/SKILL.md", "/.agents/skills/unslop/SKILL.md"))

        if "claude-code" in self._agents:
            files.update(
                {
                    f"/home/{self._username}/.claude/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.claude/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

        if "codex" in self._agents:
            # Codex can have issues with reading skills from `~/.agents/skills`
            files.update(
                {
                    f"/home/{self._username}/.codex/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.codex/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

        if "cursor-cli" in self._agents or "cursor-desktop" in self._apps:
            # Cursor can read skills from `~/.agents/skills` but cannot sync them for Cursor Cloud Agents
            files.update(
                {
                    f"/home/{self._username}/.cursor/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.cursor/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/ai-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

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
        if "grok-build" in self._agents:
            custom_pkgs.add(
                aur.CustomPackage(
                    pkgname="grok-build-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "grok-build-nosarch")
                )
            )

        # Apps
        if "cursor-desktop" in self._apps:
            custom_pkgs.add(
                aur.CustomPackage(
                    pkgname="cursor-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "cursor-nosarch")
                )
            )

        # Control planes
        if "openchamber" in self._control_planes:
            custom_pkgs.add(
                aur.CustomPackage(
                    pkgname="openchamber-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "openchamber-nosarch")
                )
            )

        if "t3code-cli" in self._control_planes:
            custom_pkgs.add(
                aur.CustomPackage(
                    pkgname="t3code-cli-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "t3code-cli-nosarch")
                )
            )

        return custom_pkgs

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        brew_casks: set[str] = set()

        # Agents
        if "claude-code" in self._agents:
            brew_casks.add("claude-code@latest")

        return brew_casks

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        brew_formulae: set[str] = set()

        # Agents
        if "gemini-cli" in self._agents:
            brew_formulae.add("gemini-cli")

        if "omp" in self._agents:
            brew_formulae.add("can1357/tap/omp")

        if "copilot-cli" in self._agents:
            brew_formulae.add("copilot-cli")

        return brew_formulae


# For reference
# Agents:
# - antigravity-cli -> not setup yet
# - claude-code -> homebrew.casks
# - codex -> pacman.packages
# - copilot-cli -> homebrew.formulae
# - cursor-cli -> not setup yet
# - devin-cli -> not setup yet
# - gemini-cli -> homebrew.formulae
# - grok-build -> aur.custom_packages
# - kilocode -> aur.packages
# - omp -> homebrew.formulae
# - opencode -> pacman.packages
# - pi -> not setup yet
#
# Apps:
# - chatgpt-desktop -> aur.packages
# - claude-desktop -> aur.packages
# - cursor-desktop -> aur.custom_packages
# - devin-desktop -> aur.packages
# - github-copilot-app -> not setup yet
# - opencode-desktop -> not setup yet
#
# Control planes:
# - openchamber -> aur.custom_packages
# - t3code-cli -> aur.custom_packages
# - t3code-desktop -> aur.packages
# - zeron -> not setup yet
