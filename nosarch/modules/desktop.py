import decman
import utils.gpu_vendor
from config import CONFIG
from decman import Directory, File
from decman.plugins import aur, flatpak, pacman, systemd
from modules.theme import get_current_theme
from utils.chassis_type import has_battery, is_laptop

gpu_vendor: str = utils.gpu_vendor.get_gpu_vendor()


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
        files: dict[str, File] = {
            f"/home/{CONFIG['%USER%']}/.config/environment.d/defaults.conf": File(
                source_file="../dotfiles/root/home/username/config/environment.d/defaults.conf",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/user-dirs.dirs": File(
                source_file="../dotfiles/root/home/username/config/user-dirs.dirs",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.config/xdg-terminals.list": File(
                source_file="../dotfiles/root/home/username/config/xdg-terminals.list",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

        def get_nvidia_env_vars() -> str:
            nvidia_env_vars: str = ""

            if gpu_vendor == "nvidia_gsp":
                nvidia_env_vars = "export NVD_BACKEND=direct\nexport LIBVA_DRIVER_NAME=nvidia\nexport __GLX_VENDOR_LIBRARY_NAME=nvidia"
            elif gpu_vendor == "nvidia_non_gsp":
                nvidia_env_vars = (
                    "export NVD_BACKEND=egl\nexport __GLX_VENDOR_LIBRARY_NAME=nvidia"
                )

            return nvidia_env_vars

        if gpu_vendor == "nvidia_gsp" or gpu_vendor == "nvidia_non_gsp":
            files |= {
                "/etc/mkinitcpio.conf.d/nvidia.conf": File(
                    source_file="../dotfiles/root/etc/mkinitcpio.conf.d/nvidia.conf",
                    owner="root",
                ),
                "/etc/modprobe.d/nvidia.conf": File(
                    source_file="../dotfiles/root/etc/modprobe.d/nvidia.conf",
                    owner="root",
                ),
                f"/home/{CONFIG['%USER%']}/.config/uwsm/env-nvidia": File(
                    content=get_nvidia_env_vars(),
                    owner=f"{CONFIG['%USER%']}",
                ),
            }

        return files

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

        graphics_set: set[str] = set()

        if gpu_vendor == "intel":
            graphics_set |= {
                "intel-media-driver",
                "lib32-mesa",
                "lib32-vulkan-intel",
                "libva-intel-driver",
                "libvpl",
                "mesa",
                "mesa-utils",
                "vpl-gpu-rt",
                "vulkan-mesa-layers",
                "vulkan-intel",
            }

        if gpu_vendor == "amd":
            graphics_set |= {
                "lib32-mesa",
                "lib32-vulkan-radeon",
                "mesa",
                "mesa-utils",
                "vulkan-mesa-layers",
                "vulkan-radeon",
            }

        if gpu_vendor == "nvidia_gsp":
            graphics_set |= {
                "lib32-nvidia-utils",
                "libva-nvidia-driver",
                "nvidia-open-dkms",
                "nvidia-utils",
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

        desktop_set: set[str] = {
            "hyprmoncfg",
            "hyprland-preview-share-picker-git",
            "hyprqt6engine",
            "vicinae-bin",
            "xdg-terminal-exec",
        }

        if gpu_vendor == "nvidia_non_gsp":
            desktop_set |= {
                "lib32-nvidia-580xx-utils",
                "nvidia-580xx-dkms",
                "nvidia-580xx-utils",
            }

        return desktop_set

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
