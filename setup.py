import decman
from decman.plugins import aur, flatpak, pacman, systemd


# My usage setup module
class SetupModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="setup")

    @pacman.packages
    def pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "bitwarden",  # Password manager
            "firefox",  # Web browser
            "flatpak",  # Linux app distribution
            "gnome-calculator",  # Calculator
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
            "speech-dispatcher",  # Text-to-speech daemon (optional for Firefox-based browsers)
            "sushi",  # Quick previewer for Nautilus
        }

        media_set: set[str] = {
            "celluloid",  # Video player (frontend for mpv)
            "wiremix",  # Audio Mixer TUI
        }

        virtualization_set: set[str] = {
            "libvirt",  # API for controlling virtualization engines
            "qemu-full",  # Full QEMU package
            "vde2",  # Virtual Distributed Ethernet for emulators like QEMU
            "virt-manager",  # Virtual machine manager
            "virt-viewer",  # Virtual machine viewer
            "virtualbox",  # VirtualBox virtualization platform
            "virtualbox-host-modules-arch",  # Host modules for VirtualBox
            "virtualbox-host-modules-lts",  # Host modules for VirtualBox (For linux-lts kernel)
        }

        merged_set: set[str] = apps_set.union(media_set, virtualization_set)
        return merged_set

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "aether",  # Theming app for Omarchy
            "localsend-bin",  # Cross-platform file sharing app
            "zen-browser-bin",  # Web browser
        }

        media_set: set[str] = {
            "stacher7"  # yt-dlp frontend
        }

        virtualization_set: set[str] = {
            "bridge-utils"  # Utils for configuring Linux ethernet bridge
        }

        merged_set: set[str] = apps_set.union(media_set, virtualization_set)
        return merged_set

    @flatpak.packages
    def flatpak_pkgs(self) -> set[str]:
        return {
            "it.mijorus.gearlever",  # AppImage Manager
        }

    @systemd.units
    def systemd_services(self) -> set[str]:
        return {"libvirtd.service"}
