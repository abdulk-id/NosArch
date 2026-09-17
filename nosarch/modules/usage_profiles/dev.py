from typing import override

import decman
import user_config.config_reader as userConfig
import utils.dotfile.dev_lang_config
import utils.paths
from decman import File, Store
from decman.plugins import aur, flatpak, pacman, systemd
from plugins import homebrew

userConfig.load()
_username: str = userConfig.get_str("user.username")
_agents: list[str] = userConfig.get_str_list("dev.agents")
_editors: list[str] = userConfig.get_str_list("dev.editors")


class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev_profile")
        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/dev-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/dev-root", _username
        )

    @override
    def on_change(self, store: Store) -> None:
        _ = decman.prg(cmd=["mise", "install"], user=_username, mimic_login=True)
        _ = decman.prg(cmd=["mise", "prune"], user=_username, mimic_login=True)

    @override
    @staticmethod
    def on_disable() -> None:
        import decman
        import user_config.config_reader as userConfig

        # `on_disable` hooks run before everything else (after `before_update` hooks), so mise would still be present.
        # needed to remove all mise installed tools
        # TODO: If this runs after mise has been removed, this command will fail.
        _ = decman.prg(cmd=["mise", "implode"], user=userConfig.get_str("user.username"), mimic_login=True)

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%USER%": _username}

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
                f"/home/{_username}/.config/mise/config.toml": File(
                    content=utils.dotfile.dev_lang_config.get_mise_config_contents(), owner=f"{_username}"
                )
            }
        )

        if _editors.__contains__("neovim"):
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
                    f"/home/{_username}/.config/nvim/.neoconf.json": File(
                        source_file="../dotfiles/dev-root/home/username/dot_config/nvim/.neoconf.json",
                        owner=f"{_username}",
                    )  # This file is handled separately because using `self._userhome_dotfiles.files()` requires that
                    # hidden files start with the `dot_` prefix. This file is part of lazyvim and should not modified by
                    # NosArch, so therefore, cannot be prefixed with `dot_`.
                }
            )

        if _editors.__contains__("zed"):
            files.update(self._userhome_dotfiles.files("/.config/zed/settings.json"))

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
        if _agents.__contains__("codex"):
            pkgs.add("openai-codex")

        if _agents.__contains__("opencode"):
            pkgs.add("opencode")

        # Code Editors
        if _editors.__contains__("neovim"):
            pkgs.update({"ast-grep", "fd", "luarocks", "neovim", "tectonic"})

        if _editors.__contains__("code-oss"):
            pkgs.add("code")

        if _editors.__contains__("zed"):
            pkgs.add("zed")

        return pkgs

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        aur_pkgs: set[str] = set()

        # Agents
        if _agents.__contains__("kilocode"):
            aur_pkgs.add("kilo-bin")

        if _agents.__contains__("codex") or _agents.__contains__("opencode") or _agents.__contains__("claude-code"):
            # Only install T3-Code if the providers it supports are installed
            aur_pkgs.add("t3code-bin")

        # Code Editors
        if _editors.__contains__("codium"):
            aur_pkgs.add("vscodium-bin")

        if _editors.__contains__("jetbrains"):
            aur_pkgs.add("jetbrains-toolbox")

        if _editors.__contains__("vscode"):
            aur_pkgs.add("visual-studio-code-bin")

        return aur_pkgs

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{_username}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}}

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        if _agents.__contains__("claude-code"):
            return {"claude-code@latest"}
        else:
            return set()

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        brew_formulae: set[str] = set()

        # Agents
        if _agents.__contains__("gemini-cli"):
            brew_formulae.add("gemini-cli")

        if _agents.__contains__("omp"):
            brew_formulae.add("can1357/tap/omp")

        if _agents.__contains__("copilot-cli"):
            brew_formulae.add("copilot-cli")

        return brew_formulae

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {f"{_username}": {"podman.socket"}}
