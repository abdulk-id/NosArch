from typing import override

import decman
import utils.dotfile.dev_lang_config
from config import CONFIG
from decman import Directory, File
from decman.plugins import aur, flatpak, pacman, systemd
from plugins import homebrew


class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev_profile")

    @override
    def file_variables(self) -> dict[str, str]:
        return CONFIG

    @override
    def directories(self) -> dict[str, Directory]:
        user_config_directories: dict[str, Directory] = {
            f"/home/{CONFIG['%USER%']}/.config/nvim/": Directory(
                source_directory="../dotfiles/dev-root/home/username/config/nvim/", owner=f"{CONFIG['%USER%']}"
            ),
            f"/home/{CONFIG['%USER%']}/.config/zed/": Directory(
                source_directory="../dotfiles/dev-root/home/username/config/zed/", owner=f"{CONFIG['%USER%']}"
            ),
        }

        return user_config_directories | {
            "/usr/local/share/nosarch-dev/": Directory(
                source_directory="../dotfiles/dev-root/usr/local/share/nosarch-dev/", owner="root"
            ),
            f"/home/{CONFIG['%USER%']}/Codespace/": Directory(
                source_directory="../dotfiles/dev-root/home/username/Codespace/", owner=f"{CONFIG['%USER%']}"
            ),
            f"/home/{CONFIG['%USER%']}/.agents/": Directory(
                source_directory="../dotfiles/dev-root/home/username/agents/", owner=f"{CONFIG['%USER%']}"
            ),
        }

    @override
    def files(self) -> dict[str, File]:
        mise_config_file: File = File(
            content=utils.dotfile.dev_lang_config.get_mise_config_contents(), owner=f"{CONFIG['%USER%']}"
        )

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
            # User Home file
            f"/home/{CONFIG['%USER%']}/.config/mise/config.toml": mise_config_file,
            f"/home/{CONFIG['%USER%']}/.config/environment.d/dev.conf": File(
                source_file="../dotfiles/dev-root/home/username/config/environment.d/dev.conf",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/environment.d/languages.conf": File(
                source_file="../dotfiles/dev-root/home/username/config/environment.d/languages.conf",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.bashrc.d/dev.bashrc": File(
                source_file="../dotfiles/dev-root/home/username/bashrc.d/dev.bashrc", owner=f"{CONFIG['%USER%']}"
            ),
            f"/home/{CONFIG['%USER%']}/.ideavimrc": File(
                source_file="../dotfiles/dev-root/home/username/dot_ideavimrc", owner=f"{CONFIG['%USER%']}"
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
        return {f"{CONFIG['%USER%']}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}}
    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        return {"claude-code"}

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {f"{CONFIG['%USER%']}": {"podman.socket"}}
