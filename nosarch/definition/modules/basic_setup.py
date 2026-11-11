from typing import override

import nosarch.engine
import nosarch.utils.paths
from nosarch.definition.user_config import UserConfigReader
from nosarch.engine import File
from nosarch.engine.steps import aur, pacman, systemd


class BasicSetupModule(nosarch.engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="basic_setup")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username
        self._vms_enabled: bool = self._user_config.setups.basic.enable_virtualization

        self._userhome_dotfiles: nosarch.utils.paths.UserhomeDotfiles = nosarch.utils.paths.UserhomeDotfiles(
            "basic-setup-root", self._username
        )

    @override
    def files(self) -> dict[str, File]:
        return self._userhome_dotfiles.files(
            "/.config/obsidian/user-flags.conf", "/.local/share/applications/dua-cli.desktop"
        )

    @pacman.packages
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

        if self._vms_enabled:
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

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        aur_pkgs_set: set[str] = {"spotify", "spotify-adblock"}

        if self._vms_enabled:
            aur_pkgs_set.update(
                {
                    "bridge-utils"  # Utils for configuring Linux ethernet bridge
                }
            )

        return aur_pkgs_set

    @systemd.units
    def systemd_services(self) -> set[str]:
        systemd_services: set[str] = set()

        if self._vms_enabled:
            systemd_services.add("libvirtd.service")

        return systemd_services
