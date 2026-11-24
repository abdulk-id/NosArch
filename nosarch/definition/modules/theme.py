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


def _first_wallpaper() -> str:
    wallpapers: list[str] = [entry.name for entry in os.scandir(_wallpaper_dir()) if entry.is_file()]
    return wallpapers[0]


def wallpaper_path(username: str, *, lockscreen: bool = False) -> str:
    # hyprpaper decides the image type from the filename. A link with no extension is not a wallpaper.
    stem: str = "current-lockscreen-wallpaper" if lockscreen else "current-wallpaper"
    extension: str = os.path.splitext(_first_wallpaper())[1]
    return f"/home/{username}/.local/share/nosarch/current-theme/{stem}{extension}"


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
        wallpaper: str = f"/home/{self._username}/.local/share/nosarch/current-theme/wallpapers/{_first_wallpaper()}"
        return {
            wallpaper_path(self._username): Symlink(target=wallpaper, owner=f"{self._username}"),
            wallpaper_path(self._username, lockscreen=True): Symlink(target=wallpaper, owner=f"{self._username}"),
        }
