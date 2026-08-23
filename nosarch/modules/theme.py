import os
from typing import override

import decman
import user_config.config_reader as userConfig
from decman import Directory, Symlink

# Change this import statement to change active theme
from themes.nosarch_blue_dark.nosarch_blue_dark import THEME

userConfig.load()
_username: str = userConfig.get_str("user.username")


def get_current_theme() -> dict[str, str]:
    return THEME


# Theming module
class ThemingModule(decman.Module):
    def __init__(self):
        super().__init__(name="theming")

    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{_username}/.local/share/nosarch/current-theme/wallpapers": Directory(
                source_directory=f"./themes/{THEME['%FILENAME%']}/wallpapers", owner=f"{_username}"
            )
        }

    def symlinks(self) -> dict[str, str | Symlink]:
        # Would break if symlinks were made BEFORE the directories were created
        return {
            f"/home/{_username}/.local/share/nosarch/current-theme/current-wallpaper": Symlink(
                target=f"/home/{_username}/.local/share/nosarch/current-theme/wallpapers/{self.choose_first_wallpaper()}",
                owner=f"{_username}",
            ),
            f"/home/{_username}/.local/share/nosarch/current-theme/current-lockscreen-wallpaper": Symlink(
                target=f"/home/{_username}/.local/share/nosarch/current-theme/wallpapers/{self.choose_first_wallpaper()}",
                owner=f"{_username}",
            ),
        }

    def choose_first_wallpaper(self) -> str:
        wallpapers: list[str] = [
            entry.name for entry in os.scandir(f"./themes/{THEME['%FILENAME%']}/wallpapers/") if entry.is_file()
        ]

        return wallpapers[0]
