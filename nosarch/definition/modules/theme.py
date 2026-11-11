import os
from typing import override

import nosarch.engine

# Change this import to change the active theme.
from nosarch.definition.themes.nosarch_blue_dark.nosarch_blue_dark import THEME
from nosarch.definition.user_config import UserConfigReader
from nosarch.engine import Directory, Symlink


def get_current_theme() -> dict[str, str]:
    return THEME


class ThemingModule(nosarch.engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="theming")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

    @override
    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{self._username}/.local/share/nosarch/current-theme/wallpapers": Directory(
                source_directory=f"./definition/themes/{THEME['%FILENAME%']}/wallpapers", owner=f"{self._username}"
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
        wallpapers: list[str] = [
            entry.name
            for entry in os.scandir(f"./definition/themes/{THEME['%FILENAME%']}/wallpapers/")
            if entry.is_file()
        ]

        return wallpapers[0]
