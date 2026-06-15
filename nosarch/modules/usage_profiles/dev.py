import decman
from config import CONFIG
from decman import File
from decman.plugins import aur, flatpak, pacman


# Dev Setup module
class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev_profile")

    def file_variables(self) -> dict[str, str]:
        return CONFIG

    def files(self) -> dict[str, File]:
        return {
            f"/home/{CONFIG['%USER%']}/.gitconfig": File(
                source_file="../dotfiles/root/home/username/dot_gitconfig",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.ideavimrc": File(
                source_file="../dotfiles/root/home/username/dot_ideavimrc",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        return {
            "ast-grep",  # Needed for Neovim
            "bash-completion",
            "cmake",
            "docker",
            "docker-compose",
            "docker-buildx",
            "fd",  # Faster `find`; Needed for Neovim
            "git",
            "lazydocker",
            "lazygit",
            "llvm",
            "luarocks",  # Needed for Neovim
            "mise",  # Language tooling manager
            "meson",
            "nasm",
            "neovim",
            "ninja",
            "opencode",
            "tectonic",  # Needed for Neovim
            "zed",
        }

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        return {"t3code-bin"}

    @flatpak.user_packages
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {
            f"{CONFIG['%USER%']}": {"me.iepure.devtoolbox", "io.github.shiftey.Desktop"}
        }
