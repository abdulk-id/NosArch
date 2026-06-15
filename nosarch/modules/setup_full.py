import decman
from config import CONFIG
from decman.plugins import aur, flatpak, pacman, systemd


# Full Setup module
class FullSetupModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="setup_full")

    @pacman.packages
    def pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "dua-cli",  # Disk usage analyzer
            "libreoffice-fresh",
            "obsidian",
            "obs-studio",
            "proton-vpn-cli",  # Official ProtonVPN CLI
            "proton-vpn-gtk-app",  # ProtonVPN GTK app (community-maintained)
            "transmission-gtk",  # BitTorrent client
        }

        virtualization_set: set[str] = {
            "libvirt",  # Virtualization library
            "qemu-full",  # Full QEMU package
            "vde2",  # Virtual Distributed Ethernet for emulators like QEMU
            "virt-manager",  # Virtual machine manager
            "virt-viewer",  # Virtual machine viewer
        }

        merged_set: set[str] = apps_set.union(virtualization_set)
        return merged_set

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "spotify",
            "spotify-adblock",
            "stacher7",  # yt-dlp frontend
            "webcord-bin",  # Discord client for Wayland
        }

        virtualization_set: set[str] = {
            "bridge-utils"  # Utils for configuring Linux ethernet bridge
        }

        merged_set: set[str] = apps_set.union(virtualization_set)
        return merged_set

    @flatpak.user_packages
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{CONFIG['%USER%']}": {"io.github.alainm23.planify"}}

    @systemd.units
    def systemd_services(self) -> set[str]:
        return {"libvirtd.service"}
