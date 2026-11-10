from typing import override

import engine
import utils.apply
import utils.paths
from engine import File
from engine.steps import pacman
from user_config import UserConfigReader


class CreativeSetupModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="creative_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/creative-setup-root", self._username
        )

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.files("/.config/hypr/app-windows/davinci.lua")

    @override
    def on_change(self, changes: engine.Changes) -> None:
        if changes.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            utils.apply.reload_hyprland()

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
