import decman
import utils.cpu_vendor
import utils.wireless_regdom
from config import CONFIG
from decman import Directory, File
from decman.plugins import aur, pacman, systemd
from utils.chassis_type import has_battery, is_laptop
from utils.luks_uuid import get_luks_uuid

cpu_vendor: str = utils.cpu_vendor.get_cpu_vendor()


# Base system module
class SystemModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="system")

    def file_variables(self) -> dict[str, str]:
        system_variables: dict[str, str] = {"%LUKS_UUID%": get_luks_uuid()}

        return CONFIG | system_variables

    def directories(self) -> dict[str, Directory]:
        etc_dirs: dict[str, Directory] = {
            "/etc/default/": Directory(source_directory="../dotfiles/root/etc/default/", owner="root"),
            "/etc/greetd/": Directory(source_directory="../dotfiles/root/etc/greetd/", owner="root"),
            "/etc/NetworkManager/": Directory(source_directory="../dotfiles/root/etc/NetworkManager/", owner="root"),
            "/etc/snapper/configs/": Directory(source_directory="../dotfiles/root/etc/snapper/configs/", owner="root"),
            "/etc/pacman.d/hooks/": Directory(source_directory="../dotfiles/root/etc/pacman.d/hooks/", owner="root"),
            "/etc/sysctl.d/": Directory(source_directory="../dotfiles/root/etc/sysctl.d/", owner="root"),
            "/etc/systemd/": Directory(source_directory="../dotfiles/root/etc/systemd/", owner="root"),
            "/etc/tmpfiles.d/": Directory(source_directory="../dotfiles/root/etc/tmpfiles.d/", owner="root"),
            "/etc/udev/rules.d/": Directory(source_directory="../dotfiles/root/etc/udev/rules.d/", owner="root"),
            "/etc/ufw/": Directory(source_directory="../dotfiles/root/etc/ufw/", owner="root"),
            "/etc/wireplumber/": Directory(source_directory="../dotfiles/root/etc/wireplumber/", owner="root"),
        }

        return etc_dirs | {
            "/usr/local/bin/util/": Directory(
                source_directory="../dotfiles/root/usr/local/bin/util/",
                owner="root",
                permissions=0o755,  # Make executable
            ),
            "/usr/lib/nosarch/": Directory(
                source_directory="../dotfiles/root/usr/lib/nosarch/",
                owner="root",
                permissions=0o755,  # Make executable
            ),
            "/usr/lib/systemd/user/": Directory(
                source_directory="../dotfiles/root/usr/lib/systemd/user/", owner="root"
            ),
        }

    def files(self) -> dict[str, File]:
        etc_files: dict[str, File] = {
            "/etc/modules-load.d/zram.conf": File(
                source_file="../dotfiles/root/etc/modules-load.d/zram.conf", owner="root"
            ),
            "/etc/mkinitcpio.conf": File(source_file="../dotfiles/root/etc/mkinitcpio.conf", owner="root"),
            "/etc/profile.d/nosarch.sh": File(
                source_file="../dotfiles/root/etc/profile.d/nosarch.sh", owner="root", permissions=0o644
            ),
            "/etc/pacman.conf": File(source_file="../dotfiles/root/etc/pacman.conf", owner="root"),
            "/etc/updatedb.conf": File(source_file="../dotfiles/root/etc/updatedb.conf", owner="root"),
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
                source_file=f"../dotfiles/root/usr/local/bin/nosarch/{name}",
                owner="root",
                permissions=0o755,  # Make executable
            )

        return (
            etc_files
            | nosarch_scripts
            | {
                f"/home/{CONFIG['%USER%']}/.bash_profile": File(
                    source_file="../dotfiles/root/home/username/dot_bashprofile", owner=f"{CONFIG['%USER%']}"
                ),
                f"/home/{CONFIG['%USER%']}/.bashrc": File(
                    source_file="../dotfiles/root/home/username/dot_bashrc", owner=f"{CONFIG['%USER%']}"
                ),
                f"/home/{CONFIG['%USER%']}/.gitconfig": File(
                    source_file="../dotfiles/root/home/username/dot_gitconfig", owner=f"{CONFIG['%USER%']}"
                ),
            }
        )

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

        if is_laptop() or has_battery():
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

    @aur.packages
    def system_aur_packages(self) -> set[str]:
        return {"limine-mkinitcpio-hook", "limine-snapper-sync", "yay-bin"}

    @systemd.units
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

        if is_laptop() or has_battery():
            systemd_set.add("power-profiles-daemon.service")

        if cpu_vendor == "GenuineIntel":
            systemd_set.add("intel_lpmd.service")
            systemd_set.add("thermald.service")

        return systemd_set


# nosarch_scripts: dict[str, File] = {
#    "/usr/local/bin/nosarch/nosarch-battery": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-battery",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-capture": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-capture",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-launch-app": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-launch-app",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-launch-tui": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-launch-tui",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-launcher": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-launcher",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-package": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-package",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-record": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-record",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-session": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-session",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-share": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-share",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-toggle": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-toggle",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
#    "/usr/local/bin/nosarch/nosarch-wellbeing": File(
#        source_file="../dotfiles/root/usr/local/bin/nosarch-wellbeing",
#        owner="root",
#        permissions=0o755,  # Make executable
#    ),
# }
