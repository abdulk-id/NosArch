import decman
from decman.plugins import aur, pacman, systemd
from utils.user_config_reader import UserConfigReader


class SetupModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="setup")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "celluloid",  # Video player (frontend for mpv)
            "firefox",
            "gnome-calculator",
            "gnome-clocks",
            "gnome-disk-utility",
            "loupe",  # Image viewer
            "nautilus",  # File manager
            "nautilus-python",  # Python bindings for Nautilus extension API; Needed for Custom Actions in Nautilus
            "papers",  # Document viewer
            "seahorse",  # Password and Keys GUI
        }

        return apps_set

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "localsend-bin",  # Cross-platform file sharing app
            "zen-browser-bin",
        }

        return apps_set

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def systemd_user_services(self) -> dict[str, set[str]]:
        return {f"{self._username}": {"nosarch-eyesight-reminder.timer"}}
