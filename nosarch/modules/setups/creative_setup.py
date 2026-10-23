from typing import override

import decman
import utils.apply
import utils.change_tracker
import utils.paths
from decman import File
from decman.plugins import pacman
from user_config import UserConfigReader


class CreativeSetupModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="creative_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/creative-setup-root", self._username
        )
        self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.tracked_files(self._tracker, "/.config/hypr/app-windows/davinci.lua")

    @override
    def on_change(self, store: decman.Store) -> None:
        if self._tracker.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            utils.apply.reload_hyprland()

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
