from typing import override

import decman
import user_config.config_reader as userConfig
import utils.dotfile.dev_lang_config
from decman import Directory, File, Store
from decman.plugins import aur, flatpak, pacman, systemd
from plugins import homebrew

userConfig.load()
_username: str = userConfig.get_str("user.username")


class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev_profile")

    @override
    def on_change(self, store: Store) -> None:
        _ = decman.prg(cmd=["mise", "install"], user=_username, mimic_login=True)
        _ = decman.prg(cmd=["mise", "prune"], user=_username, mimic_login=True)

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%USER%": _username}

    @override
    def directories(self) -> dict[str, Directory]:
        user_config_directories: dict[str, Directory] = {
            f"/home/{_username}/.config/nvim/": Directory(
                source_directory="../dotfiles/dev-root/home/username/config/nvim/", owner=f"{_username}"
            ),
            f"/home/{_username}/.config/zed/": Directory(
                source_directory="../dotfiles/dev-root/home/username/config/zed/", owner=f"{_username}"
            ),
        }

        return user_config_directories | {
            "/usr/local/share/nosarch-dev/": Directory(
                source_directory="../dotfiles/dev-root/usr/local/share/nosarch-dev/", owner="root"
            ),
            f"/home/{_username}/Codespace/": Directory(
                source_directory="../dotfiles/dev-root/home/username/Codespace/", owner=f"{_username}"
            ),
            f"/home/{_username}/.agents/": Directory(
                source_directory="../dotfiles/dev-root/home/username/agents/", owner=f"{_username}"
            ),
        }

    @override
    def files(self) -> dict[str, File]:
        return {
            # /etc files
            "/etc/containers/registries.conf.d/10-unqualified-search-registries.conf": File(
                source_file="../dotfiles/dev-root/etc/containers/registries.conf.d/10-unqualified-search-registries.conf",
                owner="root",
            ),
            "/etc/containers/registries.conf.d/01-registries.conf": File(
                source_file="../dotfiles/dev-root/etc/containers/registries.conf.d/01-registries.conf", owner="root"
            ),
            # /usr files
            "/usr/local/bin/nosarch/nosarch-dev": File(
                source_file="../dotfiles/dev-root/usr/local/bin/nosarch/nosarch-dev",
                owner="root",
                permissions=0o755,  # Make executable
            ),
            # User home folder
            f"/home/{_username}/.config/mise/config.toml": File(
                content=utils.dotfile.dev_lang_config.get_mise_config_contents(), owner=f"{_username}"
            ),
            f"/home/{_username}/.config/environment.d/dev.conf": File(
                source_file="../dotfiles/dev-root/home/username/config/environment.d/dev.conf", owner=f"{_username}"
            ),
            f"/home/{_username}/.config/environment.d/languages.conf": File(
                source_file="../dotfiles/dev-root/home/username/config/environment.d/languages.conf",
                owner=f"{_username}",
            ),
            f"/home/{_username}/.bashrc.d/dev.bashrc": File(
                source_file="../dotfiles/dev-root/home/username/bashrc.d/dev.bashrc", owner=f"{_username}"
            ),
            f"/home/{_username}/.ideavimrc": File(
                source_file="../dotfiles/dev-root/home/username/dot_ideavimrc", owner=f"{_username}"
            ),
        }

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        return {
            "ast-grep",  # Needed for Neovim
            "bash-completion",
            "cmake",
            "fd",  # Faster `find`; Needed for Neovim
            "github-cli",
            "lazygit",
            "llvm",
            "luarocks",  # Needed for Neovim
            "mise",  # Language tooling manager
            "meson",
            "neovim",
            "ninja",
            "openai-codex",
            "opencode",
            "podman",
            "podman-compose",
            "podman-docker",
            "podman-desktop",
            "tectonic",  # Needed for Neovim
            "zed",
        }

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return {"t3code-bin"}

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{_username}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}}

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        return {"claude-code"}

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {f"{_username}": {"podman.socket"}}
