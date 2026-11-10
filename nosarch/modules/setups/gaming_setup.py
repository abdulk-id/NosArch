from typing import override

import engine
import utils.apply
import utils.paths
from engine import File
from engine.steps import aur, pacman
from user_config import UserConfigReader


class GamingSetupModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="gaming_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/gaming-setup-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/gaming-setup-root", self._username
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
    def on_change(self, changes: engine.Changes) -> None:
        if changes.files_changed_in_dirs(f"/home/{self._username}/.config/hypr"):
            utils.apply.reload_hyprland()

        # Read at boot. Unloading xpad while a controller is in use is not safe, so a change waits for reboot.
        if changes.files_changed("/etc/modprobe.d/blacklist-xpad.conf", "/etc/modules-load.d/gaming-controllers.conf"):
            utils.apply.request_reboot("gaming controller modules")

        if changes.files_changed("/etc/modules-load.d/windows-compat.conf"):
            utils.apply.request_reboot("NT synchronization module")

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
