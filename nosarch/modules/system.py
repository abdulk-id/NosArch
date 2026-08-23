from typing import override

import decman
import user_config.config_reader as userConfig
import utils.hardware.chassis_type
import utils.hardware.cpu_vendor
import utils.luks_uuid
import utils.wireless_regdom
from decman import Directory, File
from decman.plugins import aur, pacman, systemd

userConfig.load()
_username: str = userConfig.get_str("user.username")

cpu_vendor: str = utils.hardware.cpu_vendor.get_cpu_vendor()


class SystemModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="system")

    @override
    def file_variables(self) -> dict[str, str]:
        return {
            "%LUKS_UUID%": utils.luks_uuid.get_luks_uuid(),
            "%FULLNAME%": userConfig.get_str("user.fullname"),
            "%GIT_EMAIL%": userConfig.get_str("user.git_email"),
        }

    @override
    def directories(self) -> dict[str, Directory]:
        etc_dirs: dict[str, Directory] = {
            "/etc/default/": Directory(source_directory="../dotfiles/system-root/etc/default/", owner="root"),
            "/etc/greetd/": Directory(source_directory="../dotfiles/system-root/etc/greetd/", owner="root"),
            "/etc/NetworkManager/": Directory(
                source_directory="../dotfiles/system-root/etc/NetworkManager/", owner="root"
            ),
            "/etc/pacman.d/hooks/": Directory(
                source_directory="../dotfiles/system-root/etc/pacman.d/hooks/", owner="root"
            ),
            "/etc/snapper/configs/": Directory(
                source_directory="../dotfiles/system-root/etc/snapper/configs/", owner="root"
            ),
            "/etc/sysctl.d/": Directory(source_directory="../dotfiles/system-root/etc/sysctl.d/", owner="root"),
            "/etc/systemd/": Directory(source_directory="../dotfiles/system-root/etc/systemd/", owner="root"),
            "/etc/tmpfiles.d/": Directory(source_directory="../dotfiles/system-root/etc/tmpfiles.d/", owner="root"),
            "/etc/udev/rules.d/": Directory(source_directory="../dotfiles/system-root/etc/udev/rules.d/", owner="root"),
            "/etc/ufw/": Directory(source_directory="../dotfiles/system-root/etc/ufw/", owner="root"),
            "/etc/wireplumber/": Directory(source_directory="../dotfiles/system-root/etc/wireplumber/", owner="root"),
        }

        return etc_dirs | {
            "/usr/lib/nosarch/": Directory(
                source_directory="../dotfiles/system-root/usr/lib/nosarch/",
                owner="root",
                permissions=0o755,  # Make executable
            ),
            "/usr/lib/systemd/user/": Directory(
                source_directory="../dotfiles/system-root/usr/lib/systemd/user/", owner="root"
            ),
            "/usr/local/bin/util/": Directory(
                source_directory="../dotfiles/system-root/usr/local/bin/util/",
                owner="root",
                permissions=0o755,  # Make executable
            ),
        }

    @override
    def files(self) -> dict[str, File]:
        etc_files: dict[str, File] = {
            "/etc/modules-load.d/zram.conf": File(
                source_file="../dotfiles/system-root/etc/modules-load.d/zram.conf", owner="root"
            ),
            "/etc/profile.d/nosarch.sh": File(
                source_file="../dotfiles/system-root/etc/profile.d/nosarch.sh", owner="root", permissions=0o644
            ),
            "/etc/mkinitcpio.conf": File(source_file="../dotfiles/system-root/etc/mkinitcpio.conf", owner="root"),
            "/etc/pacman.conf": File(source_file="../dotfiles/system-root/etc/pacman.conf", owner="root"),
            "/etc/updatedb.conf": File(source_file="../dotfiles/system-root/etc/updatedb.conf", owner="root"),
        }

        wireless_regdom: str | None = utils.wireless_regdom.get_wireless_regdom_contents()
        if wireless_regdom:
            etc_files.update(
                {
                    "/etc/conf.d/wireless-regdom": File(
                        content="# Wireless regulatory domain configuration\n\n" + wireless_regdom, owner="root"
                    )
                }
            )

        nosarch_script_names: set[str] = {
            "nosarch-battery",
            "nosarch-capture",
            "nosarch-launch-app",
            "nosarch-launch-tui",
            "nosarch-launcher",
            "nosarch-package",
            "nosarch-record",
            "nosarch-session",
            "nosarch-share",
            "nosarch-toggle",
            "nosarch-wellbeing",
        }

        nosarch_scripts: dict[str, File] = {}
        for name in nosarch_script_names:
            nosarch_scripts[f"/usr/local/bin/nosarch/{name}"] = File(
                source_file=f"../dotfiles/system-root/usr/local/bin/nosarch/{name}",
                owner="root",
                permissions=0o755,  # Make executable
            )

        return (
            etc_files
            | nosarch_scripts
            | {
                f"/home/{_username}/.bash_profile": File(
                    source_file="../dotfiles/system-root/home/username/dot_bashprofile", owner=f"{_username}"
                ),
                f"/home/{_username}/.bashrc": File(
                    source_file="../dotfiles/system-root/home/username/dot_bashrc", owner=f"{_username}"
                ),
                f"/home/{_username}/.gitconfig": File(
                    source_file="../dotfiles/system-root/home/username/dot_gitconfig", owner=f"{_username}"
                ),
            }
        )

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
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
            "python-dbus-fast",  # Installed for battery monitoring `/usr/lib/nosarch/nosarch-battery-monitor.py`
            "snapper",
            "sudo",
            "systemd-resolvconf",
            "udftools",
            "udisks2",
            "unzip",
            "usbutils",
            "xfsprogs",
            "zram-generator",
        }

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            system_set.add("power-profiles-daemon")

        if cpu_vendor == "GenuineIntel":
            system_set.add("intel-ucode")
            system_set.add("intel-lpmd")
            system_set.add("thermald")
        elif cpu_vendor == "AuthenticAMD":
            system_set.add("amd-ucode")

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

        merged_set: set[str] = system_set.union(security_set, connectivity_set)
        return merged_set

    # Packages causing issues when running decman
    decman.pacman.ignored_packages |= {"kernel-modules-hook"}

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def system_aur_packages(self) -> set[str]:
        return {
            "decman",  # Decman itself
            "limine-mkinitcpio-hook",
            "limine-snapper-sync",
            "yay-bin",
        }

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def system_services(self) -> set[str]:
        systemd_set: set[str] = {
            "apparmor.service",
            "bluetooth.service",
            "greetd.service",
            "limine-snapper-sync.service",
            "NetworkManager.service",
            "udisks2.service",
            "ufw.service",
            "swap-swapfile.swap",
        }

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            systemd_set.add("power-profiles-daemon.service")

        if cpu_vendor == "GenuineIntel":
            systemd_set.add("intel_lpmd.service")
            systemd_set.add("thermald.service")

        return systemd_set
