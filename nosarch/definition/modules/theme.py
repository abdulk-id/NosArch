import os
from typing import override

import nosarch.engine
import nosarch.utils.paths

# Change this import to change the active theme.
from nosarch.definition.themes.nosarch_blue_dark.nosarch_blue_dark import THEME
from nosarch.definition.user_config import UserConfigReader
from nosarch.engine import Directory, Symlink


def get_current_theme() -> dict[str, str]:
    return THEME


def _wallpaper_dir() -> str:
    return nosarch.utils.paths.in_package("definition", "themes", THEME["%FILENAME%"], "wallpapers")


class ThemingModule(nosarch.engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="theming")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

    @override
    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{self._username}/.local/share/nosarch/current-theme/wallpapers": Directory(
                source_directory=_wallpaper_dir(), bin_files=True, owner=f"{self._username}"
            )
        }

    @override
    def symlinks(self) -> dict[str, str | Symlink]:
        # To test: Would break if symlinks were made BEFORE the directories were created
        return {
            f"/home/{self._username}/.local/share/nosarch/current-theme/current-wallpaper": Symlink(
                target=f"/home/{self._username}/.local/share/nosarch/current-theme/wallpapers/{self._choose_first_wallpaper()}",
                owner=f"{self._username}",
            ),
            f"/home/{self._username}/.local/share/nosarch/current-theme/current-lockscreen-wallpaper": Symlink(
                target=f"/home/{self._username}/.local/share/nosarch/current-theme/wallpapers/{self._choose_first_wallpaper()}",
                owner=f"{self._username}",
            ),
        }

    def _choose_first_wallpaper(self) -> str:
        wallpapers: list[str] = [entry.name for entry in os.scandir(_wallpaper_dir()) if entry.is_file()]

        return wallpapers[0]
