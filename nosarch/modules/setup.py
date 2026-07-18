import decman
from config import CONFIG
from decman.plugins import aur, pacman, systemd


# Minimal Setup module
class SetupModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="setup")

    @pacman.packages
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

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "localsend-bin",  # Cross-platform file sharing app
            "zen-browser-bin",
        }

        return apps_set

    @systemd.user_units
    def systemd_user_services(self) -> dict[str, set[str]]:
        return {f"{CONFIG['%USER%']}": {"nosarch-eyesight-reminder.timer"}}
