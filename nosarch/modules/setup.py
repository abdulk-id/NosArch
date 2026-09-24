from typing import override

import decman
import utils.paths
from decman import File
from decman.plugins import aur, pacman, systemd
from utils.user_config_reader import UserConfigReader


class SetupModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="setup_full")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")

        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/setup-full-root", self._username
        )

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.files(
            "/.config/obsidian/user-flags.conf", "/.local/share/applications/dua-cli.desktop"
        )

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        pkgs_set: set[str] = {
            "dua-cli",  # Disk usage analyzer
            "kdeconnect",
            "libreoffice-fresh",
            "obsidian",
            "proton-vpn-cli",
            "proton-vpn-gtk-app",
            "transmission-gtk",
        }

        if self._user_config.get_bool("full_setup.enable_virtualization"):
            pkgs_set.update(
                {
                    "libvirt",
                    "qemu-full",
                    "vde2",  # Virtual Distributed Ethernet for emulators like QEMU
                    "virt-manager",
                    "virt-viewer",
                }
            )

        return pkgs_set

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        aur_pkgs_set: set[str] = {
            "spotify",
            "spotify-adblock",
            "stacher7",  # yt-dlp frontend
            "whatsie-git",
        }

        if self._user_config.get_bool("full_setup.enable_virtualization"):
            aur_pkgs_set.update(
                {
                    "bridge-utils"  # Utils for configuring Linux ethernet bridge
                }
            )

        return aur_pkgs_set

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def systemd_services(self) -> set[str]:
        systemd_services: set[str] = set()

        if self._user_config.get_bool("full_setup.enable_virtualization"):
            systemd_services.add("libvirtd.service")

        return systemd_services
