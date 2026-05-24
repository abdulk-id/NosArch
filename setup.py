import decman
from decman.plugins import aur, flatpak, pacman, systemd

from config import CONFIG


# My usage setup module
class SetupModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="setup")

    @pacman.packages
    def pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "firefox",  # Web browser
            "gnome-calculator",  # Calculator
            "gnome-clocks",  # Clock
            "gnome-disk-utility",  # Disk utility
            "libreoffice-fresh",  # Office suite
            "loupe",  # Image viewer
            "nautilus",  # File manager
            "nautilus-python",  # Python bindings for Nautilus extension API
            "obs-studio",  # Recording software
            "obsidian",  # Note-taking
            "papers",  # Document viewer
            "proton-vpn-cli",  # Official ProtonVPN CLI
            "proton-vpn-gtk-app",  # ProtonVPN GTK app (community-maintained)
            "seahorse",  # Password and Keys GUI
            "transmission-gtk",  # BitTorrent client
        }

        media_set: set[str] = {
            "celluloid",  # Video player (frontend for mpv)
        }

        virtualization_set: set[str] = {
            "libvirt",  # API for controlling virtualization engines
            "qemu-full",  # Full QEMU package
            "vde2",  # Virtual Distributed Ethernet for emulators like QEMU
            "virt-manager",  # Virtual machine manager
            "virt-viewer",  # Virtual machine viewer
        }

        merged_set: set[str] = apps_set.union(media_set, virtualization_set)
        return merged_set

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "localsend-bin",  # Cross-platform file sharing app
            "spotify",
            "spotify-adblock",
            "zen-browser-bin",  # Web browser
            "zoom",  # Online meetings
        }

        media_set: set[str] = {
            "stacher7",  # yt-dlp frontend
        }

        virtualization_set: set[str] = {
            "bridge-utils"  # Utils for configuring Linux ethernet bridge
        }

        merged_set: set[str] = apps_set.union(media_set, virtualization_set)
        return merged_set

    @flatpak.user_packages
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{CONFIG['%USER%']}": {"io.github.alainm23.planify"}}

    @systemd.units
    def systemd_services(self) -> set[str]:
        return {"libvirtd.service"}

    @systemd.user_units
    def systemd_user_services(self) -> dict[str, set[str]]:
        return {
            f"{CONFIG['%USER%']}": {
                "nosarch-eyesight-reminder.timer",
            }
        }
