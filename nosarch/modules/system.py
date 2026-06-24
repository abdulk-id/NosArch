import decman
from config import CONFIG
from decman import Directory, File
from decman.plugins import aur, pacman, systemd
from utils.chassis_type import has_battery, is_laptop
from utils.luks_uuid import get_luks_uuid


# Base system module
class SystemModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="system")

    def file_variables(self) -> dict[str, str]:
        system_variables: dict[str, str] = {
            "%LUKS_UUID%": get_luks_uuid(),
        }

        return CONFIG | system_variables

    def directories(self) -> dict[str, Directory]:
        return {
            "/etc/": Directory(
                source_directory="../dotfiles/root/etc/",
                bin_files=False,
                encoding="UTF-8",
                owner="root",
            ),
            "/usr/local/bin/": Directory(
                source_directory="../dotfiles/root/usr/local/bin/",
                bin_files=False,
                encoding="UTF-8",
                owner="root",
                permissions=0o754,  # Make executable
            ),
        }

    def files(self) -> dict[str, File]:
        return {
            f"/home/{CONFIG['%USER%']}/.bash_profile": File(
                source_file="../dotfiles/root/home/username/dot_bashprofile",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.bashrc": File(
                source_file="../dotfiles/root/home/username/dot_bashrc",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.gitconfig": File(
                source_file="../dotfiles/root/home/username/dot_gitconfig",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

    # Packages ===
    @pacman.packages
    def system_packages(self) -> set[str]:
        system_set: set[str] = {
            "base",
            "base-devel",
            "btop",
            "btrfs-assistant",
            "btrfs-progs",
            "clang",
            "cryptsetup",
            "dosfstools",
            "efibootmgr",
            "exfatprogs",
            "f2fs-tools",
            "git",
            "greetd",
            "greetd-tuigreet",
            "limine",
            "linux",
            "linux-headers",
            "linux-lts",
            "linux-lts-headers",
            "linux-firmware",
            "man-db",
            "nano",
            "memtest86+-efi",
            "snapper",
            "sudo",
            "systemd-resolvconf",
            "thermald",
            "udftools",
            "udisks2",
            "unzip",
            "usbutils",
            "xfsprogs",
            "zram-generator",
        }

        if is_laptop() or has_battery():
            system_set.add("power-profiles-daemon")

        system_intel_set: set[str] = {"intel-ucode"}

        security_set: set[str] = {"apparmor", "firewalld", "lynis", "ufw"}

        connectivity_set: set[str] = {
            "bluez",
            "bluez-utils",
            "bolt",
            "dnsmasq",
            "gvfs",
            "gvfs-afc",
            "gvfs-dnssd",
            "gvfs-gphoto2",
            "gvfs-mtp",
            "gvfs-nfs",
            "gvfs-smb",
            "inetutils",
            "libimobiledevice",
            "networkmanager",
            "usbmuxd",
            "wget",
            "wireless-regdb",
        }

        merged_set: set[str] = system_set.union(
            system_intel_set, security_set, connectivity_set
        )
        return merged_set

    # Packages causing issues when running decman
    decman.pacman.ignored_packages |= {"kernel-modules-hook"}

    @aur.packages
    def system_aur_packages(self) -> set[str]:
        return {
            "limine-mkinitcpio-hook",
            "yay-bin",
        }

    @systemd.units
    def system_services(self) -> set[str]:
        return {
            "apparmor.service",
            "bluetooth.service",
            "greetd.service",
            "NetworkManager.service",
            "power-profiles-daemon.service",
            "udisks2.service",
            "ufw.service",
        }
