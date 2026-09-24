from typing import override

import decman
import modules.theme
import utils.change_tracker
import utils.dotfile.mimeapps_list
import utils.hardware.chassis_type
import utils.hardware.gpu_vendor
import utils.paths
from decman import File
from decman.plugins import aur, flatpak, pacman, systemd
from utils.user_config_reader import UserConfigReader

_gpu_vendor: str = utils.hardware.gpu_vendor.get_gpu_vendor()


class DesktopModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="desktop")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")

        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/desktop-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/desktop-root", self._username
        )
        self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()

    @override
    def on_change(self, store: decman.Store) -> None:
        # GSettings reads compiled cache, not .override files, so the cache has to be rebuilt.
        # TODO only on glib schema file update
        _ = decman.prg(cmd=["glib-compile-schemas", "/usr/share/glib-2.0/schemas"])

    @override
    def file_variables(self) -> dict[str, str]:
        return modules.theme.get_current_theme()

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        # ~/ files
        files.update(self._userhome_dotfiles.files("/Templates/Textfile.txt"))

        # ~/.config/ files
        files.update(
            self._userhome_dotfiles.files(
                "/.config/btop/btop.conf",
                "/.config/elephant/menus/capture.lua",
                "/.config/elephant/menus/main.lua",
                "/.config/elephant/menus/packages.lua",
                "/.config/elephant/menus/power.lua",
                "/.config/elephant/menus/record.lua",
                "/.config/elephant/menus/session.lua",
                "/.config/elephant/menus/settings.lua",
                "/.config/elephant/menus/share.lua",
                "/.config/elephant/desktopapplications.toml",
                "/.config/elephant/menus.toml",
                "/.config/elephant/websearch.toml",
                "/.config/environment.d/defaults.conf",
                "/.config/ghostty/config",
                "/.config/ghostty/theme.conf",
                "/.config/gtk-3.0/settings.ini",
                "/.config/gtk-4.0/settings.ini",
                "/.config/hypr/app-windows/1password.lua",
                "/.config/hypr/app-windows/bitwarden.lua",
                "/.config/hypr/app-windows/browsers.lua",
                "/.config/hypr/app-windows/chromium.lua",
                "/.config/hypr/app-windows/core.lua",
                "/.config/hypr/app-windows/firefox.lua",
                "/.config/hypr/app-windows/gearlever.lua",
                "/.config/hypr/app-windows/localsend.lua",
                "/.config/hypr/app-windows/nosarch-dash.lua",
                "/.config/hypr/app-windows/qemu.lua",
                "/.config/hypr/app-windows/spotify.lua",
                "/.config/hypr/binds/hyprbinds.lua",
                "/.config/hypr/binds/mediabinds.lua",
                "/.config/hypr/binds/userbinds.lua",
                "/.config/hypr/.luarc.json",
                "/.config/hypr/application-style.conf",
                "/.config/hypr/autostart.lua",
                "/.config/hypr/hypridle.conf",
                "/.config/hypr/hyprland.lua",
                "/.config/hypr/hyprlock.conf",
                "/.config/hypr/hyprpaper.conf",
                "/.config/hypr/hyprqt6engine.conf",
                "/.config/hypr/hyprsunset.conf",
                "/.config/hypr/hyprtoolkit.conf",
                "/.config/hypr/input.lua",
                "/.config/hypr/looknfeel.lua",
                "/.config/hypr/permissions.lua",
                "/.config/hypr/windows.lua",
                "/.config/hypr/xdph.conf",
                "/.config/hyprland-preview-share-picker/config.yaml",
                "/.config/hyprland-preview-share-picker/style.css",
                "/.config/satty/config.toml",
                "/.config/swaync/config.json",
                "/.config/swaync/style.css",
                "/.config/swayosd/config.toml",
                "/.config/swayosd/style.css",
                "/.config/systemd/user/nosarch-eyesight-reminder.service",
                "/.config/systemd/user/nosarch-eyesight-reminder.timer",
                "/.config/uwsm/env",
                "/.config/uwsm/env-hyprland",
                "/.config/uwsm/fcitx",
                "/.config/uwsm/wayland",
                "/.config/walker/config.toml",
                "/.config/walker/themes/nosarch/layout.xml",
                "/.config/walker/themes/nosarch/style.css",
                "/.config/waybar/config.jsonc",
                "/.config/waybar/style.css",
                "/.config/xdg-desktop-portal/portals.conf",
                "/.config/user-dirs.dirs",
                "/.config/xdg-terminals.list",
            )
        )

        # ~/.local/ files
        files.update(
            self._userhome_dotfiles.files(
                "/.local/share/nautilus-python/extensions/localsend-share.py",
                "/.local/share/nautilus-python/extensions/open-in-terminal.py",
            )
        )
        files.update(
            {
                f"/home/{self._username}/.local/share/applications/mimeapps.list": File(
                    content=utils.dotfile.mimeapps_list.get_mimeapps_content(), owner=f"{self._username}"
                )
            }
        )

        # /usr files
        files.update(
            self._dotfiles.files(
                "/usr/share/glib-2.0/schemas/90-nosarch-localsearch.gschema.override",
                "/usr/share/wayland-sessions/nosarch/nosarch-hyprland.desktop",
            )
        )

        ## NosArch scripts
        files.update(
            self._dotfiles.files(
                "/usr/local/bin/nosarch/nosarch-capture",
                "/usr/local/bin/nosarch/nosarch-launch-app",
                "/usr/local/bin/nosarch/nosarch-launch-tui",
                "/usr/local/bin/nosarch/nosarch-launcher",
                "/usr/local/bin/nosarch/nosarch-record",
                "/usr/local/bin/nosarch/nosarch-share",
                "/usr/local/bin/nosarch/nosarch-toggle",
                "/usr/local/bin/nosarch/nosarch-wellbeing",
                "/usr/local/bin/util/detect-screen-sharing.sh",
                permissions=0o755,  # Make executable
            )
        )

        # Conditional files
        ## Nvidia config
        def get_nvidia_uwsm_user_config() -> str:
            nvidia_env_vars: str = ""

            if _gpu_vendor == "nvidia_gsp":
                nvidia_env_vars = "export NVD_BACKEND=direct\nexport LIBVA_DRIVER_NAME=nvidia\nexport __GLX_VENDOR_LIBRARY_NAME=nvidia"
            elif _gpu_vendor == "nvidia_non_gsp":
                nvidia_env_vars = "export NVD_BACKEND=egl\nexport __GLX_VENDOR_LIBRARY_NAME=nvidia"

            return nvidia_env_vars

        if _gpu_vendor == "nvidia_gsp" or _gpu_vendor == "nvidia_non_gsp":
            files.update(self._dotfiles.files("/etc/mkinitcpio.conf.d/nvidia.conf", "/etc/modprobe.d/nvidia.conf"))
            files.update(
                {
                    f"/home/{self._username}/.config/uwsm/env-nvidia": File(
                        content=get_nvidia_uwsm_user_config(), owner=f"{self._username}"
                    )
                }
            )

        return files

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        desktop_set: set[str] = {
            "fcitx5",
            "fcitx5-gtk",
            "fcitx5-qt",
            "ffmpeg",  # Used for webcam recording
            "flatpak",
            "flatseal",  # Flatpak permission manager
            "ghostty",
            "gnome-text-editor",
            "gpu-screen-recorder",  # Used for screen recording
            "grim",  # Screenshot utility
            "hyprcursor",
            "hypridle",
            "hyprland",
            "hyprland-qt-support",
            "hyprlock",
            "hyprpaper",
            "hyprpicker",
            "hyprpolkitagent",
            "hyprshutdown",
            "hyprsunset",
            "noto-fonts",
            "noto-fonts-cjk",
            "noto-fonts-emoji",
            "qt5-wayland",
            "qt6-wayland",
            "quickshell",
            "satty",  # Screenshot annotation tool
            "slurp",  # Region selection tool (used for screenshots)
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

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            desktop_set.add("brightnessctl")

        config_set: set[str] = {"bluetui"}

        graphics_set: set[str] = set()

        if _gpu_vendor == "intel":
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

        if _gpu_vendor == "amd":
            graphics_set |= {
                "lib32-mesa",
                "lib32-vulkan-radeon",
                "mesa",
                "mesa-utils",
                "vulkan-mesa-layers",
                "vulkan-radeon",
            }

        if _gpu_vendor == "nvidia_gsp":
            graphics_set |= {"lib32-nvidia-utils", "libva-nvidia-driver", "nvidia-open-dkms", "nvidia-utils"}

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

        merged_set: set[str] = desktop_set.union(
            config_set, graphics_set, media_set, printer_set, utilities_set, apps_set
        )
        return merged_set

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        # Packages that are no longer used by NosArch.
        # Config files of these packages are still present in the repo.
        # unused_aur_pkgs: set[str] = {"vicinae-bin"}

        desktop_set: set[str] = {
            "elephant-bin",
            "elephant-calc-bin",
            "elephant-clipboard-bin",
            "elephant-desktopapplications-bin",
            "elephant-files-bin",
            "elephant-menus-bin",
            "elephant-providerlist-bin",
            "elephant-runner-bin",
            "elephant-snippets-bin",
            "elephant-websearch-bin",
            "hyprmoncfg",
            "hyprland-preview-share-picker-git",
            "hyprqt6engine",
            "still",
            "walker-bin",
        }

        if _gpu_vendor == "nvidia_non_gsp":
            desktop_set |= {"lib32-nvidia-580xx-utils", "nvidia-580xx-dkms", "nvidia-580xx-utils"}

        apps_set: set[str] = {
            "localsend-bin",  # Cross-platform file sharing app
            "zen-browser-bin",
        }

        merged_set: set[str] = desktop_set.union(apps_set)
        return merged_set

    decman.aur.ignored_packages |= {"xdg-terminal-exec", "nosarch-dash-bin"}

    @flatpak.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_pkgs(self) -> set[str]:
        return {
            "it.mijorus.gearlever"  # AppImage Manager
        }

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def desktop_services(self) -> set[str]:
        return {"cups.socket"}

    @systemd.user_units  # pyright: ignore[reportUnknownMemberType]
    def desktop_user_services(self) -> dict[str, set[str]]:
        desktop_user_services: set[str] = {
            "elephant.service",
            "hyprmoncfgd.service",
            "pipewire.service",
            "pipewire-pulse.service",
            "wireplumber.service",
            "xdg-user-dirs.service",
            "nosarch-eyesight-reminder.timer",
        }

        if utils.hardware.chassis_type.has_battery():
            desktop_user_services.add("nosarch-battery-monitor.timer")

        return {f"{self._username}": desktop_user_services}
