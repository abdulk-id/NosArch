from typing import override

import nosarch.engine
import nosarch.utils.apply
import nosarch.utils.paths
from nosarch.definition.user_config import UserConfigReader
from nosarch.engine import File
from nosarch.engine.steps import aur, pacman


class GamingSetupModule(nosarch.engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="gaming_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._dotfiles: nosarch.utils.paths.Dotfiles = nosarch.utils.paths.Dotfiles("gaming-setup-root")
        self._userhome_dotfiles: nosarch.utils.paths.UserhomeDotfiles = nosarch.utils.paths.UserhomeDotfiles(
            "gaming-setup-root", self._username
        )

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        files.update(
            self._dotfiles.files(
                "/etc/modprobe.d/blacklist-xpad.conf",
                "/etc/modules-load.d/gaming-controllers.conf",
                "/etc/modules-load.d/windows-compat.conf",
            )
        )
        files.update(self._dotfiles.files("/usr/share/wayland-sessions/nosarch/steam-big-picture.desktop"))
        files.update(self._userhome_dotfiles.files("/.config/hypr/app-windows/steam.lua"))
        files.update(self._userhome_dotfiles.files("/.local/bin/steamos-session-select", permissions=0o754))
        # 0o754 - Make executable

        return files

    @override
    def on_change(self, changes: nosarch.engine.Changes) -> None:
        if changes.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            nosarch.utils.apply.reload_hyprland()

        # Read at boot. Unloading xpad while a controller is in use is not safe, so a change waits for reboot.
        if changes.files_changed("/etc/modprobe.d/blacklist-xpad.conf", "/etc/modules-load.d/gaming-controllers.conf"):
            nosarch.utils.apply.request_reboot("gaming controller modules")

        if changes.files_changed("/etc/modules-load.d/windows-compat.conf"):
            nosarch.utils.apply.request_reboot("NT synchronization module")

    @pacman.packages
    def pkgs(self) -> set[str]:
        game_launchers: set[str] = {"lutris", "steam"}

        gaming_utilities: set[str] = {
            "gamescope",  # Micro-compositor for gaming (with support for Steam)
            "lib32-mangohud",
            "mangohud",  # Performance statistics overlay
        }

        return game_launchers.union(gaming_utilities, {"discord"})

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        return {
            "xpadneo-dkms"  # Xbox controller driver
        }
