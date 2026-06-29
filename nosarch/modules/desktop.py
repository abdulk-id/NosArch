import decman
from config import CONFIG
from decman import Directory, File
from decman.plugins import aur, flatpak, pacman, systemd
from modules.theme import get_current_theme
from utils.chassis_type import has_battery, is_laptop
from utils.gpu_lib32_drivers import get_lib32_gpu_drivers


# Desktop module
class DesktopModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="desktop")

    def file_variables(self) -> dict[str, str]:
        return CONFIG | get_current_theme()

    def directories(self) -> dict[str, Directory]:
        user_config_directories: dict[str, Directory] = {
            f"/home/{CONFIG['%USER%']}/.config/btop/": Directory(
                source_directory="../dotfiles/root/home/username/config/btop/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/environment.d/": Directory(
                source_directory="../dotfiles/root/home/username/config/environment.d/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/ghostty/": Directory(
                source_directory="../dotfiles/root/home/username/config/ghostty/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/gtk-3.0/": Directory(
                source_directory="../dotfiles/root/home/username/config/gtk-3.0/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/gtk-4.0": Directory(
                source_directory="../dotfiles/root/home/username/config/gtk-4.0/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/hypr/": Directory(
                source_directory="../dotfiles/root/home/username/config/hypr/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/hyprland-preview-share-picker/": Directory(
                source_directory="../dotfiles/root/home/username/config/hyprland-preview-share-picker/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/swaync/": Directory(
                source_directory="../dotfiles/root/home/username/config/swaync/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/swayosd/": Directory(
                source_directory="../dotfiles/root/home/username/config/swayosd/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/systemd/user/": Directory(
                source_directory="../dotfiles/root/home/username/config/systemd/user/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/uwsm/": Directory(
                source_directory="../dotfiles/root/home/username/config/uwsm/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/vicinae/": Directory(
                source_directory="../dotfiles/root/home/username/config/vicinae/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/waybar/": Directory(
                source_directory="../dotfiles/root/home/username/config/waybar/",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/xdg-desktop-portal/": Directory(
                source_directory="../dotfiles/root/home/username/config/xdg-desktop-portal/",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

        user_script_directories: dict[str, Directory] = {
            f"/home/{CONFIG['%USER%']}/.local/bin/nosarch/": Directory(
                source_directory="../dotfiles/root/home/username/local/bin/nosarch/",
                owner=f"{CONFIG['%USER%']}",
                permissions=0o754,  # Make executable
            ),
            f"/home/{CONFIG['%USER%']}/.local/bin/util/": Directory(
                source_directory="../dotfiles/root/home/username/local/bin/util/",
                owner=f"{CONFIG['%USER%']}",
                permissions=0o754,  # Make executable
            ),
        }

        return (
            user_config_directories
            | user_script_directories
            | {
                f"/home/{CONFIG['%USER%']}/.local/share/": Directory(
                    source_directory="../dotfiles/root/home/username/local/share/",
                    owner=f"{CONFIG['%USER%']}",
                ),
                f"/home/{CONFIG['%USER%']}/Templates/": Directory(
                    source_directory="../dotfiles/root/home/username/Templates/",
                    owner=f"{CONFIG['%USER%']}",
                ),
            }
        )

    def files(self) -> dict[str, File]:
        return {
            f"/home/{CONFIG['%USER%']}/.config/user-dirs.dirs": File(
                source_file="../dotfiles/root/home/username/config/user-dirs.dirs",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/xdg-terminals.list": File(
                source_file="../dotfiles/root/home/username/config/xdg-terminals.list",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    @pacman.packages
    def pkgs(self) -> set[str]:
        desktop_set: set[str] = {
            "fcitx5",
            "fcitx5-gtk",
            "fcitx5-qt",
            "flatpak",
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
            "imagemagick",  # TODO: Installed why?
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

        if is_laptop() or has_battery():
            desktop_set.add("brightnessctl")

        config_set: set[str] = {
            "bluetui",
        }

        graphics_set: set[str] = {
            "mesa",
            "mesa-utils",
            "vulkan-mesa-layers",
        }
        graphics_set |= get_lib32_gpu_drivers()

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

    # Ignored because needed for testing, not for user setups
    decman.pacman.ignored_packages |= {"icon-library", "dconf-editor"}

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
        }

    @systemd.user_units
    def desktop_user_services(self) -> dict[str, set[str]]:
        desktop_user_services: set[str] = {
            "hyprmoncfgd.service",
            "pipewire.service",
            "pipewire-pulse.service",
            "wireplumber.service",
            "xdg-user-dirs.service",
        }

        if has_battery():
            desktop_user_services.add("nosarch-battery-monitor.service")

        return {f"{CONFIG['%USER%']}": desktop_user_services}
