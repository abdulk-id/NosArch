import decman
from decman import File
from decman.plugins import aur, flatpak, pacman

from config import CONFIG


# My dev setup module
class DevModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="dev")

    def files(self) -> dict[str, File]:
        return {
            f"/home/{CONFIG['%USER%']}/.gitconfig": File(
                source_file="./root/home/username/dot_gitconfig",
                bin_file=False,
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        return {
            "bash-completion",
            "docker",
            "docker-compose",
            "docker-buildx",
            "fzf",
            "git",
            "gum",
            "jq",
            "lazydocker",
            "lazygit",
            "llvm",
            "mise",
            "opencode",
            "vim",
            "zed",
        }

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        return {"visual-studio-code-bin"}

    @flatpak.packages
    def flatpak_pkgs(self) -> set[str]:
        return {"me.iepure.devtoolbox"}
