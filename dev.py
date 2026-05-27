import decman
from decman import File
from decman.plugins import flatpak, pacman

from config import CONFIG


# My dev setup module
class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev")

    def file_variables(self) -> dict[str, str]:
        return CONFIG

    def files(self) -> dict[str, File]:
        return {
            f"/home/{CONFIG['%USER%']}/.gitconfig": File(
                source_file="./root/home/username/dot_gitconfig",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.ideavimrc": File(
                source_file="./root/home/username/dot_ideavimrc",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        return {
            "ast-grep",
            "bash-completion",
            "cmake",  # Cross-platform and open-source make system
            "code",  # OSS version of VSCode
            "docker",  # Docker CLI
            "docker-compose",
            "docker-buildx",
            "fd",
            "git",  # Git version control
            "lazydocker",  # Docker TUI
            "lazygit",  # Git TUI
            "llvm",  # "Compiler infrastructure"
            "luarocks",
            "mise",
            "meson",  # Build system
            "nasm",  # Assembler
            "neovim",
            "ninja",  # Small speed-focused build system
            "opencode",  # OpenCode AI Agent
            "tectonic",
            "vim",
            "zed",  # Zed Code Editor
        }

    @flatpak.user_packages
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {
            f"{CONFIG['%USER%']}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}
        }
