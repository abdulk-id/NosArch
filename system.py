import decman
from decman import File
from decman.plugins import aur, pacman, systemd

from config import CONFIG


# Base system module
class SystemModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="system")

    def file_variables(self) -> dict[str, str]:
        return CONFIG

    def files(self) -> dict[str, File]:
        system_config_files: dict[str, File] = {
            "/etc/greetd/config.toml": File(
                source_file="./root/etc/greetd/config.toml",
                bin_file=False,
                encoding="UTF-8",
                owner="root",
            ),
            "/etc/NetworkManager/conf.d/wifi-powersave.conf": File(
                source_file="./root/etc/NetworkManager/conf.d/wifi-powersave.conf",
                bin_file=False,
                encoding="UTF-8",
                owner="root",
            ),
            "/etc/systemd/logind.conf.d/10-ignore-power-button.conf": File(
                source_file="./root/etc/systemd/logind.conf.d/10-ignore-power-button.conf",
                bin_file=False,
                encoding="UTF-8",
                owner="root",
            ),
            "/etc/systemd/system.conf.d/10-faster-shutdown.conf": File(
                source_file="./root/etc/systemd/system.conf.d/10-faster-shutdown.conf",
                bin_file=False,
                encoding="UTF-8",
                owner="root",
            ),
            "/etc/systemd/zram-generator.conf": File(
                source_file="./root/etc/systemd/zram-generator.conf",
                bin_file=False,
                encoding="UTF-8",
                owner="root",
            ),
        }

        user_config_files: dict[str, File] = {
            f"/home/{CONFIG['%USER%']}/.bash_profile": File(
                source_file="./root/home/username/dot_bashprofile",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
            f"/home/{CONFIG['%USER%']}/.bashrc": File(
                source_file="./root/home/username/dot_bashrc",
                bin_file=False,
                encoding="UTF-8",
                owner=f"{CONFIG['%USER%']}",
            ),
        }

        merged_dict: dict[str, File] = system_config_files | user_config_files
        return merged_dict

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
            "power-profiles-daemon",
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

        system_intel_set: set[str] = {"intel-ucode"}

        security_set: set[str] = {"apparmor", "clamav", "firewalld", "ufw"}

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
        system_set: set[str] = {
            "limine-mkinitcpio-hook",
            "yay-bin",
        }

        connectivity_set: set[str] = {"ufw-docker"}

        merged_set: set[str] = system_set.union(connectivity_set)
        return merged_set

    @systemd.units
    def system_services(self) -> set[str]:
        return {
            "apparmor.service",
            "bluetooth.service",
            # "clamav-daemon.service",
            # "clamav-freshclam.service",
            "greetd.service",
            "NetworkManager.service",
            "power-profiles-daemon.service",
            "udisks2.service",
            "ufw.service",
        }
