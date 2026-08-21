from typing import override

import decman
from config import CONFIG
from decman import File
from decman.plugins import aur, pacman


# Gaming Setup module
class GamingModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="gaming_profile")

    @override
    def files(self) -> dict[str, File]:
        return {
            "/etc/modprobe.d/blacklist-xpad.conf": File(
                source_file="../dotfiles/gaming-root/etc/modprobe.d/blacklist-xpad.conf", owner="root"
            ),
            "/etc/modules-load.d/windows-compat.conf": File(
                source_file="../dotfiles/gaming-root/etc/modules-load.d/windows-compat.conf", owner="root"
            ),
            "/etc/modules-load.d/gaming-controllers.conf": File(
                source_file="../dotfiles/gaming-root/etc/modules-load.d/gaming-controllers.conf", owner="root"
            ),
            "/usr/share/wayland-sessions/steam-big-picture.desktop": File(
                source_file="../dotfiles/gaming-root/usr/share/wayland-sessions/steam-big-picture.desktop", owner="root"
            ),
            f"/home/{CONFIG['%USER%']}/.local/bin/steamos-session-select": File(
                source_file="../dotfiles/gaming-root/home/username/local/bin/steamos-session-select",
                owner=CONFIG["%USER%"],
                permissions=0o754,  # Make executable
            ),
        }

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        game_launchers: set[str] = {"lutris", "steam"}

        gaming_utilities: set[str] = {
            "gamescope",  # Micro-compositor for gaming (with support for Steam)
            "lib32-mangohud",  # 32-bit library for mangohud
            "mangohud",  # Performance statistics overlay
        }

        return game_launchers.union(gaming_utilities)

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return {
            "xpadneo-dkms"  # Xbox controller driver
        }
