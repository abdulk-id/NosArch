from typing import override

import decman
import user_config.config_reader as userConfig
from decman import Directory
from decman.plugins import aur, flatpak, pacman, systemd

userConfig.load()
_username: str = userConfig.get_str("user.username")


class FullSetupModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="setup_full")

    @override
    def directories(self) -> dict[str, Directory]:
        return {
            f"/home/{_username}/.config/obsidian/": Directory(
                source_directory="../dotfiles/setup-full-root/home/username/config/obsidian/", owner=f"{_username}"
            )
        }

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "dua-cli",  # Disk usage analyzer
            "kdeconnect",
            "libreoffice-fresh",
            "obsidian",
            "proton-vpn-cli",
            "proton-vpn-gtk-app",
            "transmission-gtk",
        }

        virtualization_set: set[str] = {
            "libvirt",
            "qemu-full",
            "vde2",  # Virtual Distributed Ethernet for emulators like QEMU
            "virt-manager",
            "virt-viewer",
        }

        merged_set: set[str] = apps_set.union(virtualization_set)
        return merged_set

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        apps_set: set[str] = {
            "spotify",
            "spotify-adblock",
            "stacher7",  # yt-dlp frontend
        }

        virtualization_set: set[str] = {
            "bridge-utils"  # Utils for configuring Linux ethernet bridge
        }

        merged_set: set[str] = apps_set.union(virtualization_set)
        return merged_set

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {f"{_username}": {"io.github.tobagin.karere"}}

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def systemd_services(self) -> set[str]:
        return {"libvirtd.service"}
