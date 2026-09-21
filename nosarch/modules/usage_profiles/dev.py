import os
from typing import override

import decman
import utils.dotfile.dev_lang_config
import utils.paths
from decman import File, Store
from decman.plugins import aur, flatpak, pacman, systemd
from plugins import homebrew
from utils.user_config_reader import UserConfigReader

# decman reads `source.py` as text and `exec()`s it after `os.chdir`-ing into its directory,
# so package paths are resolved relative to `nosarch/`, not to this file.
_PACKAGES_DIR: str = os.path.abspath("packages")


class DevModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="dev_profile")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")
        self._agents: list[str] = self._user_config.get_str_list("dev.agents")
        self._editors: list[str] = self._user_config.get_str_list("dev.editors")

        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/dev-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/dev-root", self._username
        )

    @override
    def on_change(self, store: Store) -> None:
        _ = decman.prg(cmd=["mise", "install"], user=self._username, mimic_login=True)
        _ = decman.prg(cmd=["mise", "prune"], user=self._username, mimic_login=True)

    @override
    @staticmethod
    def on_disable() -> None:
        import decman
        from utils.user_config_reader import UserConfigReader

        # `on_disable` hooks run before everything else (after `before_update` hooks), so mise would still be present.
        # needed to remove all mise installed tools
        # TODO: If this runs after mise has been removed, this command will fail.
        _ = decman.prg(cmd=["mise", "implode"], user=UserConfigReader().get_str("user.username"), mimic_login=True)

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%USER%": self._username}

    def _t3code_needed(self) -> bool:
        return any(agent in self._agents for agent in ("claude-code", "codex", "opencode"))

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        # ~/ files
        files.update(
            self._userhome_dotfiles.files(
                "/.agents/skills/bro/SKILL.md",
                "/.agents/skills/unslop/SKILL.md",
                "/.bashrc.d/dev.bashrc",
                "/Codespace/Language-Tooling/.npmrc",
                "/Codespace/Language-Tooling/.trackerignore",
                "/Codespace/Tries/.trackerignore",
                "/.ideavimrc",
            )
        )

        if "claude-code" in self._agents:
            files.update(
                {
                    f"/home/{self._username}/.claude/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.claude/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

        if "codex" in self._agents:
            # Codex can have issues with reading skills from `~/.agents/skills`
            files.update(
                {
                    f"/home/{self._username}/.codex/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.codex/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

        if "cursor" in self._editors:
            # Cursor can read skills from `~/.agents/skills` but cannot sync them for Cursor Cloud Agents
            files.update(
                {
                    f"/home/{self._username}/.cursor/skills/bro/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/bro/SKILL.md",
                        owner=f"{self._username}",
                    ),
                    f"/home/{self._username}/.cursor/skills/unslop/SKILL.md": File(
                        source_file="../dotfiles/dev-root/home/username/dot_agents/skills/unslop/SKILL.md",
                        owner=f"{self._username}",
                    ),
                }
            )

        ## ~/.config files
        files.update(
            self._userhome_dotfiles.files(
                "/.config/environment.d/dev.conf",
                "/.config/environment.d/languages.conf",
                "/.config/hypr/app-windows/jetbrains.lua",
            )
        )
        files.update(
            {
                f"/home/{self._username}/.config/mise/config.toml": File(
                    content=utils.dotfile.dev_lang_config.get_mise_config_contents(), owner=f"{self._username}"
                )
            }
        )

        if self._editors.__contains__("neovim"):
            files.update(
                self._userhome_dotfiles.files(
                    # Neovim - Lazyvim Config
                    "/.config/nvim/lua/config/autocmds.lua",
                    "/.config/nvim/lua/config/keymaps.lua",
                    "/.config/nvim/lua/config/lazy.lua",
                    "/.config/nvim/lua/config/options.lua",
                    "/.config/nvim/lua/plugins/example.lua",
                    "/.config/nvim/init.lua",
                    "/.config/nvim/lazy-lock.json",
                    "/.config/nvim/lazyvim.json",
                    "/.config/nvim/LICENSE",
                    "/.config/nvim/README.md",
                    "/.config/nvim/stylua.toml",
                )
            )
            files.update(
                {
                    f"/home/{self._username}/.config/nvim/.neoconf.json": File(
                        source_file="../dotfiles/dev-root/home/username/dot_config/nvim/.neoconf.json",
                        owner=f"{self._username}",
                    )  # This file is handled separately because using `self._userhome_dotfiles.files()` requires that
                    # hidden files start with the `dot_` prefix. This file is part of lazyvim and should not be
                    # modified by NosArch, so therefore, cannot be prefixed with `dot_`.
                }
            )

        if self._editors.__contains__("zed"):
            files.update(self._userhome_dotfiles.files("/.config/zed/settings.json", "/.config/zed/keymap.json"))

        if self._t3code_needed():
            files.update(
                self._userhome_dotfiles.files(
                    "/.config/hypr/app-permissions/t3code.lua", "/.config/hypr/binds/t3code.lua"
                )
            )

        # /etc files
        files.update(
            self._dotfiles.files(
                "/etc/containers/registries.conf.d/10-unqualified-search-registries.conf",
                "/etc/containers/registries.conf.d/01-registries.conf",
            )
        )

        # /usr files
        ## NosArch Dev files
        files.update(self._dotfiles.files("/usr/local/bin/nosarch/nosarch-dev", permissions=0o755))
        files.update(
            self._dotfiles.files(
                "/usr/local/share/nosarch-dev/templates/java-gradle/dot_gitignore",
                "/usr/local/share/nosarch-dev/templates/java-gradle/gradle.properties",
                "/usr/local/share/nosarch-dev/templates/java-gradle/mise.toml",
                "/usr/local/share/nosarch-dev/templates/java-maven/dot_gitignore",
                "/usr/local/share/nosarch-dev/templates/java-maven/mise.toml",
                "/usr/local/share/nosarch-dev/templates/nodejs/dot_gitignore",
                "/usr/local/share/nosarch-dev/templates/nodejs/mise.toml",
                "/usr/local/share/nosarch-dev/templates/python/dot_gitignore",
                "/usr/local/share/nosarch-dev/templates/python/mise.toml",
                "/usr/local/share/nosarch-dev/templates/rust/mise.toml",
                "/usr/local/share/nosarch-dev/templates/dot_gitattributes",
            )
        )

        return files

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        pkgs: set[str] = {
            "bash-completion",
            "cmake",
            "github-cli",
            "lazygit",
            "llvm",
            "mise",  # Language tooling manager
            "meson",
            "ninja",
            "podman",
            "podman-compose",
            "podman-docker",
            "podman-desktop",
        }

        # Agents
        if self._agents.__contains__("codex"):
            pkgs.add("openai-codex")

        if self._agents.__contains__("opencode"):
            pkgs.add("opencode")

        # Code Editors
        if self._editors.__contains__("neovim"):
            pkgs.update({"ast-grep", "fd", "luarocks", "neovim", "tectonic"})

        if self._editors.__contains__("code-oss"):
            pkgs.add("code")

        if self._editors.__contains__("zed"):
            pkgs.add("zed")

        return pkgs

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        aur_pkgs: set[str] = set()

        # Agents
        if self._agents.__contains__("kilocode"):
            aur_pkgs.add("kilo-bin")

        if self._t3code_needed():
            # Only install T3-Code if the providers it supports are installed
            aur_pkgs.add("t3code-bin")

        # Code Editors
        if "codium" in self._editors:
            aur_pkgs.add("vscodium-bin")

        if "jetbrains" in self._editors:
            aur_pkgs.add("jetbrains-toolbox")

        if "vscode" in self._editors:
            aur_pkgs.add("visual-studio-code-bin")

        return aur_pkgs

    @aur.custom_packages  # pyright: ignore[reportUnknownMemberType]
    def custom_pkgs(self) -> set[aur.CustomPackage]:
        custom_pkgs: set[aur.CustomPackage] = set()

        if "cursor" in self._editors:
            custom_pkgs.add(
                aur.CustomPackage(
                    pkgname="cursor-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "cursor-nosarch")
                )
            )

        return custom_pkgs

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{self._username}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}}

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        if self._agents.__contains__("claude-code"):
            return {"claude-code@latest"}
        else:
            return set()

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        brew_formulae: set[str] = set()

        # Agents
        if self._agents.__contains__("gemini-cli"):
            brew_formulae.add("gemini-cli")

        if self._agents.__contains__("omp"):
            brew_formulae.add("can1357/tap/omp")

        if self._agents.__contains__("copilot-cli"):
            brew_formulae.add("copilot-cli")

        return brew_formulae

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {f"{self._username}": {"podman.socket"}}
