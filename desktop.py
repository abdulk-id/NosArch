import decman
from decman import Directory
from decman.plugins import aur, pacman, systemd

from config import CONFIG
from theme import THEME


# Desktop session module
class DesktopModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="desktop")

    def file_variables(self) -> dict[str, str]:
        return CONFIG | THEME

    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{CONFIG['%USER%']}/.config/": Directory(
                source_directory="./root/home/username/config/",
                bin_files=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.local/bin/": Directory(
                source_directory="./root/home/username/local/bin/",
                bin_files=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
                permissions=0o754,  # Make executable
            ),
            f"/home/{CONFIG['%USER%']}/.local/share/": Directory(
                source_directory="./root/home/username/local/share/",
                bin_files=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        desktop_set: set[str] = {
            "brightnessctl",
            "ghostty",
            "hyprcursor",
            "hypridle",
            "hyprland",
            "hyprland-qt-support",
            "hyprlock",
            "hyprpaper",
            "hyprpicker",
            "hyprpolkitagent",
            "hyprshot",
            "icon-library",
            "qt5-wayland",
            "qt6-wayland",
            "swaync",
            "swayosd",
            "ttf-jetbrains-mono-nerd",
            "uwsm",
            "waybar",
            "wayland",
            "wayland-protocols",
            "wl-clipboard",
            "xdg-desktop-portal-gtk",
            "xdg-desktop-portal-hyprland",
        }

        graphics_set: set[str] = {"mesa", "mesa-utils"}
        graphics_intel_set: set[str] = {
            "intel-gpu-tools",
            "intel-media-driver",
            "libva-intel-driver",
            "vulkan-intel",
        }

        media_set: set[str] = {
            "cups",  # CUPS daemon
            "cups-browsed",  # Helper daemon for browsing CUPS printers
            "cups-filters",  # Filters for CUPS printing
            "cups-pdf",  # PDF printing support for CUPS
            "pipewire",  # Pipewire audio/video server
            "pipewire-alsa",  # ALSA backend for Pipewire
            "pipewire-jack",  # JACK backend for Pipewire
            "pipewire-pulse",  # PulseAudio backend for Pipewire
            "playerctl",  # Player control utility
            "system-config-printer",  # System configuration tool for printers
            "wireplumber",  # WirePlumber session manager
        }

        merged_set: set[str] = desktop_set.union(
            graphics_set, graphics_intel_set, media_set
        )
        return merged_set

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        return {
            "elephant",
            "elephant-clipboard",
            "elephant-desktopapplications",
            "elephant-files",
            "elephant-menus",
            "elephant-providerlist",
            "elephant-websearch",
            "hyprdynamicmonitors-bin",
            "hyprland-preview-share-picker-git",
            "hyprqt6engine",
            "hyprshutdown",
            "walker-bin",
            "xdg-terminal-exec",
        }

    @systemd.user_units
    def desktop_services(self) -> dict[str, set[str]]:
        return {
            f"{CONFIG['%USER%']}": {
                "elephant.service",
                "hypridle.service",
                "hyprpaper.service",
                "hyprpolkitagent.service",
                "pipewire.service",
                "pipewire-pulse.service",
                "walker.service",
                "waybar.service",
                "wireplumber.service",
                "xdg-user-dirs.service",
            }
        }
