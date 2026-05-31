import os

import decman
from decman import Directory, Symlink

from config import CONFIG
from customization.themes.nosarch_blue_dark.nosarch_blue_dark import THEME


def get_current_theme() -> dict[str, str]:
    return THEME


# Theming module
class ThemingModule(decman.Module):
    def __init__(self):
        super().__init__(name="theming")

    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{CONFIG['%USER%']}/.local/share/nosarch/current-theme/wallpapers": Directory(
                source_directory=f"./customization/themes/{THEME['%FILENAME%']}/wallpapers",
                bin_files=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    def symlinks(self) -> dict[str, str | Symlink]:
        # Would break if symlinks were made BEFORE the directories were created
        return {
            f"/home/{CONFIG['%USER%']}/.local/share/nosarch/current-theme/current-wallpaper": Symlink(
                target=f"/home/{CONFIG['%USER%']}/.local/share/nosarch/current-theme/wallpapers/{self.choose_first_wallpaper()}",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.local/share/nosarch/current-theme/current-lockscreen-wallpaper": Symlink(
                target=f"/home/{CONFIG['%USER%']}/.local/share/nosarch/current-theme/wallpapers/{self.choose_first_wallpaper()}",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    def choose_first_wallpaper(self) -> str:
        wallpapers: list[str] = [
            entry.name
            for entry in os.scandir(
                f"./customization/themes/{THEME['%FILENAME%']}/wallpapers/"
            )
            if entry.is_file()
        ]

        return wallpapers[0]
