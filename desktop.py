import decman
from decman import Directory
from decman.plugins import aur, flatpak, pacman, systemd

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
            f"/home/{CONFIG['%USER%']}/Templates/": Directory(
                source_directory="./root/home/username/Templates/",
                bin_files=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        desktop_set: set[str] = {
            "brightnessctl",
            "fcitx5",
            "fcitx5-gtk",
            "fcitx5-qt",
            "flatpak",  # Linux app distribution
            "flatseal",  # Flatpak permission manager
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
            "hyprshutdown",
            "hyprsunset",
            "imagemagick",
            "qt5-wayland",
            "qt6-wayland",
            "quickshell",
            "swaync",
            "swayosd",
            "ttf-jetbrains-mono-nerd",
            "uwsm",
            "waybar",
            "wayland",
            "wayland-protocols",
            "wl-clipboard",
            "xdg-desktop-portal",
            "xdg-desktop-portal-gtk",
            "xdg-desktop-portal-hyprland",
        }

        config_set: set[str] = {
            "bluetui",
            "dconf-editor",
            "icon-library",
        }

        graphics_set: set[str] = {"mesa", "mesa-utils", "vulkan-mesa-layers"}
        graphics_intel_set: set[str] = {
            "intel-gpu-tools",
            "intel-media-driver",
            "libva-intel-driver",
            "vulkan-intel",
        }

        media_set: set[str] = {
            "alsa-utils",  # ALSA utilities
            "pipewire",  # Pipewire audio/video server
            "pipewire-alsa",  # ALSA backend for Pipewire
            "pipewire-jack",  # JACK backend for Pipewire
            "pipewire-pulse",  # PulseAudio backend for Pipewire
            "playerctl",  # Player control utility
            "wireplumber",  # WirePlumber session manager
            "wiremix",  # Audio Mixer TUI
        }

        printer_set: set[str] = {
            "cups",  # CUPS daemon
            "cups-browsed",  # Helper daemon for browsing CUPS printers
            "cups-filters",  # Filters for CUPS printing
            "cups-pdf",  # PDF printing support for CUPS
            "system-config-printer",  # System configuration tool for printers
        }

        utilities_set: set[str] = {
            "fzf",  # CLI Fuzzy finder
            "gum",  # CLI tool for glamorous shell interactions
            "jq",  # CLI JSON processor
            "tesseract",  # OCR tool
            "tesseract-data-eng",  # OCR data for English
            "zenity",  # GUI dialog box from shell commands
        }

        merged_set: set[str] = desktop_set.union(
            config_set,
            graphics_set,
            graphics_intel_set,
            media_set,
            printer_set,
            utilities_set,
        )
        return merged_set

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        # Packages that are no longer used by NosArch.
        # Config files of these packages are still present in the repo.
        unused_aur_pkgs: set[str] = {
            "elephant",
            "elephant-bookmarks",
            "elephant-calc",
            "elephant-clipboard",
            "elephant-desktopapplications",
            "elephant-files",
            "elephant-menus",
            "elephant-providerlist",
            "elephant-runner",
            "elephant-snippets",
            "elephant-websearch",
            "walker-bin",
        }

        return {
            "hyprmoncfg",
            "hyprland-preview-share-picker-git",
            "hyprqt6engine",
            "vicinae-bin",
            "xdg-terminal-exec",
        }

    @flatpak.packages
    def flatpak_pkgs(self) -> set[str]:
        return {
            "it.mijorus.gearlever",  # AppImage Manager
            "io.github.linx_systems.ClamUI",  # Clamav GUI
        }

    @systemd.user_units
    def desktop_user_services(self) -> dict[str, set[str]]:
        return {
            f"{CONFIG['%USER%']}": {
                "hyprmoncfgd.service",
                "pipewire.service",
                "pipewire-pulse.service",
                "wireplumber.service",
                "xdg-user-dirs.service",
            }
        }
