from typing import override

import decman
import user_config.config_reader as userConfig
import utils.paths
from decman import File
from decman.plugins import aur, pacman

userConfig.load()
_username: str = userConfig.get_str("user.username")


class GamingModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="gaming_profile")
        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/gaming-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/gaming-root", _username
        )

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        files.update(
            self._dotfiles.files(
                "/etc/modprobe.d/blacklist-xpad.conf",
                "/etc/modules-load.d/gaming-controllers.conf",
                "/etc/modules-load.d/windows-compat.conf",
                "/usr/share/wayland-sessions/nosarch/steam-big-picture.desktop",
            )
        )
        files.update(self._userhome_dotfiles.files("/.config/hypr/app-windows/steam.lua"))
        files.update(self._userhome_dotfiles.files("/.local/bin/steamos-session-select", permissions=0o754))
        # 0o754 - Make executable

        return files

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        game_launchers: set[str] = {"lutris", "steam"}

        gaming_utilities: set[str] = {
            "gamescope",  # Micro-compositor for gaming (with support for Steam)
            "lib32-mangohud",
            "mangohud",  # Performance statistics overlay
        }

        return game_launchers.union(gaming_utilities, {"discord"})

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return {
            "xpadneo-dkms"  # Xbox controller driver
        }
