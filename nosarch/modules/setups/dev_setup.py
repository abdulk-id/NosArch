from typing import override

import engine
import utils.apply
import utils.dotfile.dev_lang_config
import utils.paths
from engine import File
from engine.steps import aur, pacman, systemd
from user_config import UserConfigReader


class DevSetupModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="dev_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username
        self._editors: list[str] = self._user_config.setups.dev.editors

        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/dev-setup-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/dev-setup-root", self._username
        )

    @override
    def on_change(self, changes: engine.Changes) -> None:
        home: str = f"/home/{self._username}"

        if changes.files_changed_in_dirs(f"{home}/.config/hypr"):
            utils.apply.reload_hyprland()

        if changes.files_changed_in_dirs(f"{home}/.config/environment.d"):
            # Read by `systemd-environment-d-generator` when the user manager starts.
            utils.apply.request_logout("development environment variables")

        _ = engine.run(["mise", "install"], user=self._username)
        _ = engine.run(["mise", "prune"], user=self._username)

    @override
    def on_disable(self) -> None:
        # `on_disable` hooks run before every step (after `before_update` hooks), so mise would still be present.
        # needed to remove all mise installed tools
        # TODO: If this runs after mise has been removed, this command will fail.
        _ = engine.run(["mise", "implode"], user=self._username)

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%USER%": self._username}

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        # ~/ files
        files.update(
            self._userhome_dotfiles.files(
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
                        source_file="../dotfiles/dev-setup-root/home/username/dot_config/nvim/.neoconf.json",
                        owner=f"{self._username}",
                    )  # This file is handled separately because using `self._userhome_dotfiles.files()` requires that
                    # hidden files start with the `dot_` prefix. This file is part of lazyvim and should not be
                    # modified by NosArch, so therefore, cannot be prefixed with `dot_`.
                }
            )

        if self._editors.__contains__("zed"):
            files.update(self._userhome_dotfiles.files("/.config/zed/settings.json", "/.config/zed/keymap.json"))

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

        # Code Editors
        if self._editors.__contains__("neovim"):
            pkgs.update({"ast-grep", "luarocks", "neovim", "tectonic"})

        if self._editors.__contains__("code-oss"):
            pkgs.add("code")

        if self._editors.__contains__("zed"):
            pkgs.add("zed")

        return pkgs

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        aur_pkgs: set[str] = set()

        if "codium" in self._editors:
            aur_pkgs.add("vscodium-bin")

        if "jetbrains" in self._editors:
            aur_pkgs.add("jetbrains-toolbox")

        if "vscode" in self._editors:
            aur_pkgs.add("visual-studio-code-bin")

        return aur_pkgs

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {f"{self._username}": {"podman.socket"}}
