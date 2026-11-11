from typing import override

import nosarch.engine
import nosarch.utils.apply
import nosarch.utils.paths
from nosarch.definition.user_config import UserConfigReader
from nosarch.engine import File
from nosarch.engine.steps import pacman


class CreativeSetupModule(nosarch.engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="creative_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._userhome_dotfiles: nosarch.utils.paths.UserhomeDotfiles = nosarch.utils.paths.UserhomeDotfiles(
            "dotfiles/creative-setup-root", self._username
        )

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.files("/.config/hypr/app-windows/davinci.lua")

    @override
    def on_change(self, changes: nosarch.engine.Changes) -> None:
        if changes.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            nosarch.utils.apply.reload_hyprland()

    @pacman.packages
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
