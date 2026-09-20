import os
import sys
from typing import override

import decman
import user_config.config_reader as userConfig
import utils.change_tracker
import utils.dotfile.luks_uuid
import utils.dotfile.wireless_regdom
import utils.hardware.chassis_type
import utils.hardware.cpu_vendor
import utils.hardware.firmware_vendors
import utils.hardware.thunderbolt
import utils.paths
from decman import File, Store
from decman.core.output import print_info, print_list, prompt_confirm
from decman.plugins import aur, pacman, systemd

userConfig.load()
_username: str = userConfig.get_str("user.username")

_cpu_vendor: str = utils.hardware.cpu_vendor.get_cpu_vendor()


class SystemModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="system")
        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/system-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/system-root", _username
        )
        self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()

    @override
    def file_variables(self) -> dict[str, str]:
        return {
            "%LUKS_UUID%": utils.dotfile.luks_uuid.get_luks_uuid(),
            "%USER%": _username,
            "%FULLNAME%": userConfig.get_str("user.fullname"),
            "%GIT_EMAIL%": userConfig.get_str("user.git_email"),
        }

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        # /etc files
        files.update(
            self._dotfiles.tracked_files(
                self._tracker,
                "/etc/default/limine",
                "/etc/greetd/config.toml",
                "/etc/modules-load.d/zram.conf",
                "/etc/NetworkManager/conf.d/wifi-powersave.conf",
                "/etc/pacman.d/hooks/05-nosarch-package-backup.hook",
                "/etc/plymouth/plymouthd.conf",
                "/etc/snapper/configs/root",
                "/etc/sysctl.d/90-sysctl.conf",
                "/etc/sysctl.d/99-memory-parameters.conf",
                "/etc/systemd/journald.conf.d/00-journal-size.conf",
                "/etc/systemd/logind.conf.d/10-ignore-power-button.conf",
                "/etc/systemd/system/swap-swapfile.swap",
                "/etc/systemd/system.conf.d/00-service-timeouts.conf",
                "/etc/systemd/system.conf.d/10-open-file-limit.conf",
                "/etc/systemd/user.conf.d/10-open-file-limit.conf",
                "/etc/systemd/zram-generator.conf",
                "/etc/tmpfiles.d/coredump.conf",
                "/etc/udev/rules.d/20-intel-audio-powersave.rules",
                "/etc/udev/rules.d/99-auto-power-profile.rules",
                "/etc/ufw/applications.d/localsend",
                "/etc/ufw/user.rules",
                "/etc/ufw/user6.rules",
                "/etc/wireplumber/wireplumber.conf.d/bluetooth-a2dp-autoconnect.conf",
                "/etc/mkinitcpio.conf",
                "/etc/pacman.conf",
            )
        )
        files.update(self._dotfiles.tracked_files(self._tracker, "/etc/profile.d/nosarch.sh", permissions=0o644))

        wireless_regdom: str | None = utils.dotfile.wireless_regdom.get_wireless_regdom_contents()
        if wireless_regdom:
            files.update(
                {
                    "/etc/conf.d/wireless-regdom": File(
                        content="# Wireless regulatory domain configuration\n\n" + wireless_regdom, owner="root"
                    )
                }
            )

        # /usr files
        files.update(
            self._dotfiles.tracked_files(
                self._tracker,
                "/usr/lib/systemd/user/nosarch-battery-monitor.service",
                "/usr/lib/systemd/user/nosarch-battery-monitor.timer",
            )
        )

        ## Plymouth theme files
        files.update(
            self._dotfiles.tracked_files(
                self._tracker,
                "/usr/share/plymouth/themes/nosarch/bullet.png",
                "/usr/share/plymouth/themes/nosarch/entry.png",
                "/usr/share/plymouth/themes/nosarch/lock.png",
                "/usr/share/plymouth/themes/nosarch/logo.png",
                "/usr/share/plymouth/themes/nosarch/progress_bar.png",
                "/usr/share/plymouth/themes/nosarch/progress_box.png",
                bin_file=True,
            )
        )
        files.update(
            self._dotfiles.tracked_files(
                self._tracker,
                "/usr/share/plymouth/themes/nosarch/nosarch.plymouth",
                "/usr/share/plymouth/themes/nosarch/nosarch.script",
            )
        )

        ## NosArch scripts
        files.update(
            self._dotfiles.tracked_files(
                self._tracker,
                "/usr/local/bin/nosarch/nosarch-battery",
                "/usr/local/bin/nosarch/nosarch-package",
                "/usr/local/bin/nosarch/nosarch-session",
                "/usr/local/bin/util/nosarch-lock-helper.sh",
                "/usr/local/bin/util/sudo-keepalive.sh",
                permissions=0o755,  # Make executable
            )
        )

        # ~/ files
        files.update(
            self._userhome_dotfiles.tracked_files(
                self._tracker, "/.config/yay/config.json", "/.bash_profile", "/.bashrc", "/.gitconfig"
            )
        )

        return files

    @override
    def on_change(self, store: Store) -> None:
        changed_files: set[str] = self._tracker.changed

        def changed_files_in(*target_dirs: str) -> bool:
            for target_dir in target_dirs:
                target_path: str = os.path.abspath(target_dir)

                if any(os.path.commonpath([p, target_path]) == target_path for p in changed_files):
                    return True
            return False

        def files_changed(*paths: str) -> bool:
            return not changed_files.isdisjoint(paths)

        if changed_files_in("/etc/systemd/system", "/usr/lib/systemd"):
            print_info("Reloading systemd.")
            _ = decman.prg(["systemctl", "daemon-reload"])

        if changed_files_in("/etc/NetworkManager"):
            print_info("Reloading NetworkManager.")
            _ = decman.prg(["systemctl", "reload", "NetworkManager"])

        if changed_files_in("/etc/sysctl.d"):
            print_info("Applying kernel parameters.")
            _ = decman.prg(["sysctl", "--system", "--quiet"])

        if changed_files_in("/etc/systemd/journald.conf.d"):
            print_info("Restarting systemd-journald.")
            _ = decman.prg(["systemctl", "restart", "systemd-journald"])

        if changed_files_in("/etc/systemd/system.conf.d", "/etc/systemd/user.conf.d") or files_changed(
            "/etc/systemd/system.conf"
        ):
            print_info("Restarting systemd.")
            _ = decman.prg(["systemctl", "daemon-reexec"])

        if changed_files_in("/etc/tmpfiles.d"):
            print_info("Cleaning tmp files.")
            _ = decman.prg(["systemd-tmpfiles", "--create", "--clean"])

        if changed_files_in("/etc/udev/rules.d"):
            print_info("Reloading udev.")
            _ = decman.prg(["udevadm", "control", "--reload"])
            _ = decman.prg(["udevadm", "trigger", "--subsystem-match=power_supply", "--action=change"])

        if changed_files_in("/etc/ufw"):
            print_info("Restarting firewall (ufw).")
            _ = decman.prg(["systemctl", "restart", "ufw"])

        if (
            changed_files_in("/etc/modprobe.d", "/etc/mkinitcpio.conf.d", "/etc/plymouth", "/usr/share/plymouth/themes")
            or "/etc/mkinitcpio.conf" in changed_files
        ):
            print_info("Rebuilding initramfs and updating Limine boot entries.")
            _ = decman.prg(["limine-mkinitcpio"])

        # Reboot requiring changes ---
        needs_reboot: list[str] = []

        if files_changed("/etc/systemd/zram-generator.conf", "/etc/modules-load.d/zram.conf"):
            # Applying these live means swapoff on an active zram device holding
            # compressed pages, which can OOM the machine under memory pressure.
            needs_reboot.append("ZRAM configuration")

        if changed_files_in("/etc/systemd/logind.conf.d"):
            # systemd-logind has no ExecReload, and restarting it disturbs active sessions.
            needs_reboot.append("logind configuration")

        if not needs_reboot:
            return

        print_list("These changes will take effect after a reboot: ", needs_reboot, 1)

        if sys.stdin.isatty() and prompt_confirm("Reboot now?", default=False):
            _ = decman.prg(["/usr/local/bin/nosarch/nosarch-session", "restart"])

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
            "kernel-modules-hook",
            "limine",
            "linux",
            "linux-headers",
            "man-db",
            "nano",
            "memtest86+-efi",
            "plymouth",
            "snapper",
            "sudo",
            "systemd-resolvconf",
            "udisks2",
            "unzip",
            "usbutils",
            "xfsprogs",
            "zram-generator",
        }

        if userConfig.get_bool("system.enable_lts_kernel"):
            system_set.add("linux-lts")
            system_set.add("linux-lts-headers")

        # Only the `linux-firmware-*` splits this machine's hardware needs.
        # The `linux-firmware` meta package pulls every vendor split (~410 MiB).
        system_set |= utils.hardware.firmware_vendors.get_firmware_packages()

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            system_set.add("power-profiles-daemon")

        if _cpu_vendor == "GenuineIntel":
            system_set.add("intel-ucode")
            system_set.add("intel-lpmd")
            system_set.add("thermald")
        elif _cpu_vendor == "AuthenticAMD":
            system_set.add("amd-ucode")

        security_set: set[str] = {"apparmor", "firewalld", "ufw"}

        connectivity_set: set[str] = {
            "bluez",
            "bluez-utils",
            "dnsmasq",
            "gvfs",
            "gvfs-afc",
            "gvfs-dnssd",
            "gvfs-gphoto2",
            "gvfs-mtp",
            "gvfs-nfs",
            "gvfs-smb",
            "libimobiledevice",
            "networkmanager",
            "usbmuxd",
            "wget",
            "wireless-regdb",
        }

        if utils.hardware.thunderbolt.is_thunderbolt_present():
            connectivity_set.add("bolt")  # Thunderbolt device authorization

        merged_set: set[str] = system_set.union(security_set, connectivity_set)
        return merged_set

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

        if _cpu_vendor == "GenuineIntel":
            systemd_set.add("intel_lpmd.service")
            systemd_set.add("thermald.service")

        return systemd_set
