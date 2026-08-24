from typing import override

import decman
import user_config.config_reader as userConfig
from decman import File
from decman.plugins import pacman

userConfig.load()
_username: str = userConfig.get_str("user.username")


class CreativeModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="creative_profile")

    @override
    def files(self) -> dict[str, File]:
        return {
            f"/home/{_username}/.config/hypr/app-windows/davinci.lua": File(
                source_file="../dotfiles/creative-root/home/username/config/hypr/app-windows/davinci.lua",
                owner=f"{_username}",
            )
        }

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
