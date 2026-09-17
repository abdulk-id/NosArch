from typing import override

import decman
import user_config.config_reader as userConfig
import utils.paths
from decman import File
from decman.plugins import pacman

userConfig.load()
_username: str = userConfig.get_str("user.username")


class CreativeModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="creative_profile")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/creative-root", _username
        )

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.files("/.config/hypr/app-windows/davinci.lua")

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
