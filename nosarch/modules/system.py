import os
from typing import override

import engine
import utils.apply
import utils.dotfile.luks_uuid
import utils.dotfile.wireless_regdom
import utils.hardware.chassis_type
import utils.hardware.cpu_vendor
import utils.hardware.firmware_vendors
import utils.hardware.thunderbolt
import utils.paths
from engine import File
from engine.output import print_info
from engine.steps import aur, pacman, systemd
from user_config import UserConfigReader


class SystemModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="system")

        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

        self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/system-root")
        self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
            "../dotfiles/system-root", self._username
        )

    @override
    def file_variables(self) -> dict[str, str]:
        return {
            "%LUKS_UUID%": utils.dotfile.luks_uuid.get_luks_uuid(),
            "%USER%": self._username,
            "%FULLNAME%": self._user_config.user.fullname,
            "%GIT_EMAIL%": self._user_config.user.git_email,
        }

    @override
    def files(self) -> dict[str, File]:
        files: dict[str, File] = {}

        # /etc files
        files.update(
            self._dotfiles.files(
                "/etc/default/limine",
                "/etc/modules-load.d/zram.conf",
                "/etc/sddm.conf.d/10-theme.conf",
                "/etc/sddm.conf.d/10-wayland.conf",
                "/etc/NetworkManager/conf.d/wifi-powersave.conf",
                "/etc/pacman.d/hooks/05-nosarch-package-backup.hook",
                "/etc/pam.d/sddm",
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
        files.update(self._dotfiles.files("/etc/profile.d/nosarch.sh", permissions=0o644))

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
            self._dotfiles.files(
                "/usr/lib/systemd/user/nosarch-battery-monitor.service",
                "/usr/lib/systemd/user/nosarch-battery-monitor.timer",
            )
        )

        ## Plymouth theme files
        files.update(
            self._dotfiles.files(
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
            self._dotfiles.files(
                "/usr/share/plymouth/themes/nosarch/nosarch.plymouth",
                "/usr/share/plymouth/themes/nosarch/nosarch.script",
            )
        )

        ## SDDM greeter
        files.update(self._dotfiles.files("/usr/share/sddm/hyprland.lua"))
        files.update(
            self._dotfiles.files(
                "/usr/share/sddm/themes/nosarch/metadata.desktop",
                "/usr/share/sddm/themes/nosarch/theme.conf",
                "/usr/share/sddm/themes/nosarch/Main.qml",
            )
        )
        files.update(
            self._dotfiles.files(
                "/usr/share/sddm/themes/nosarch/bullet.png",
                "/usr/share/sddm/themes/nosarch/entry-failed.png",
                "/usr/share/sddm/themes/nosarch/entry.png",
                "/usr/share/sddm/themes/nosarch/lock-failed.png",
                "/usr/share/sddm/themes/nosarch/lock.png",
                "/usr/share/sddm/themes/nosarch/logo.png",
                bin_file=True,
            )
        )

        ## NosArch scripts
        files.update(
            self._dotfiles.files(
                "/usr/local/bin/nosarch/nosarch",
                "/usr/local/bin/nosarch/nosarch-battery",
                "/usr/local/bin/nosarch/nosarch-package",
                "/usr/local/bin/nosarch/nosarch-session",
                "/usr/local/bin/util/nosarch-lock-helper.sh",
                "/usr/local/bin/util/sudo-keepalive.sh",
                permissions=0o755,  # Make executable
            )
        )

        # Sourced by nosarch-package rather than run, so they are not executable. AppImage and cleanup live here
        # rather than in a packaging module because they are not gated on a packaging switch: an AppImage needs no
        # package manager, and cleanup has to survive a method's module being disabled.
        files.update(
            self._dotfiles.files(
                "/usr/local/bin/util/package/appimage.sh",
                "/usr/local/bin/util/package/cleanup.sh",
                "/usr/local/bin/util/package/common.sh",
            )
        )

        # ~/ files
        files.update(
            self._userhome_dotfiles.files("/.config/yay/config.json", "/.bash_profile", "/.bashrc", "/.gitconfig")
        )

        return files

    @override
    def before_update(self) -> None:
        self._release_display_manager_alias()

    @override
    def on_change(self, changes: engine.Changes) -> None:
        if changes.files_changed_in_dirs("/etc/systemd/system", "/usr/lib/systemd"):
            utils.apply.reload_systemd()

        if changes.files_changed_in_dirs("/etc/NetworkManager"):
            utils.apply.reload_network_manager()

        if changes.files_changed_in_dirs("/etc/sysctl.d"):
            utils.apply.apply_sysctl()

        if changes.files_changed_in_dirs("/etc/systemd/journald.conf.d"):
            utils.apply.restart_journald()

        if changes.files_changed_in_dirs(
            "/etc/systemd/system.conf.d", "/etc/systemd/user.conf.d"
        ) or changes.files_changed("/etc/systemd/system.conf"):
            utils.apply.reexec_systemd()

        if changes.files_changed_in_dirs("/etc/tmpfiles.d"):
            utils.apply.clean_tmpfiles()

        if changes.files_changed_in_dirs("/etc/udev/rules.d"):
            utils.apply.reload_udev()

        if changes.files_changed_in_dirs("/etc/ufw"):
            utils.apply.restart_ufw()

        if changes.files_changed_in_dirs(
            "/etc/modprobe.d", "/etc/mkinitcpio.conf.d", "/etc/plymouth", "/usr/share/plymouth/themes"
        ) or changes.files_changed("/etc/mkinitcpio.conf"):
            utils.apply.rebuild_initramfs()

        if changes.files_changed("/etc/systemd/zram-generator.conf", "/etc/modules-load.d/zram.conf"):
            # Applying these live means swapoff on an active zram device holding
            # compressed pages, which can OOM the machine under memory pressure.
            utils.apply.request_reboot("ZRAM configuration")

        if changes.files_changed_in_dirs("/etc/systemd/logind.conf.d"):
            # systemd-logind has no ExecReload, and restarting it disturbs active sessions.
            utils.apply.request_reboot("logind configuration")

        if changes.files_changed_in_dirs("/etc/sddm.conf.d", "/usr/share/sddm") or changes.files_changed(
            "/etc/pam.d/sddm"
        ):
            # SDDM reads this when the greeter starts. Restarting the display manager here ends the session.
            utils.apply.request_reboot("SDDM configuration")

    @override
    def after_update(self) -> None:
        self._update_limine_conf_settings()

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
            "kernel-modules-hook",
            "limine",
            "linux",
            "linux-headers",
            "man-db",
            "nano",
            "memtest86+-efi",
            "plymouth",
            "sddm",
            "snapper",
            "sudo",
            "systemd-resolvconf",
            "udisks2",
            "unzip",
            "usbutils",
            "xfsprogs",
            "zram-generator",
        }

        # makechrootpkg and mkarchroot, which the engine builds foreign packages with.
        if self._user_config.advanced.build_aur_in_clean_chroot:
            system_set.add("devtools")

        if self._user_config.advanced.enable_nosarch_works:
            system_set |= {"desktop-file-utils", "lynis", "namcap", "pacman-contrib", "shellcheck"}

        if self._user_config.system.enable_lts_kernel:
            system_set.add("linux-lts")
            system_set.add("linux-lts-headers")

        system_set |= utils.hardware.firmware_vendors.get_firmware_packages()

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            system_set.add("power-profiles-daemon")

        if utils.hardware.cpu_vendor.is_cpu_intel():
            system_set.add("intel-ucode")
            system_set.add("thermald")

            if utils.hardware.cpu_vendor.is_intel_hybrid():
                system_set.add("intel-lpmd")

        elif utils.hardware.cpu_vendor.is_cpu_amd():
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

        utility_set: set[str] = {"curl", "fd", "fzf", "gum", "jq", "ripgrep", "which"}

        if utils.hardware.thunderbolt.is_thunderbolt_present():
            connectivity_set.add("bolt")  # Thunderbolt device authorization

        merged_set: set[str] = system_set.union(security_set, connectivity_set, utility_set)
        return merged_set

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def system_aur_packages(self) -> set[str]:
        return {"limine-mkinitcpio-hook", "limine-snapper-sync"}

    @aur.custom_packages  # pyright: ignore[reportUnknownMemberType]
    def custom_pkgs(self) -> set[str]:
        return {"yay-nosarch"}

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def system_services(self) -> set[str]:
        systemd_set: set[str] = {
            "apparmor.service",
            "bluetooth.service",
            "limine-snapper-sync.service",
            "sddm.service",
            "NetworkManager.service",
            "snapper-cleanup.timer",
            "udisks2.service",
            "ufw.service",
            "swap-swapfile.swap",
        }

        if utils.hardware.chassis_type.is_laptop() or utils.hardware.chassis_type.has_battery():
            systemd_set.add("power-profiles-daemon.service")

        if utils.hardware.cpu_vendor.is_cpu_intel():
            systemd_set.add("thermald.service")

            if utils.hardware.cpu_vendor.is_intel_hybrid():
                systemd_set.add("intel_lpmd.service")

        return systemd_set

    @systemd.user_units
    def system_user_services(self) -> dict[str, set[str]]:
        return {self._username: {"gnome-keyring-daemon.service", "gcr-ssh-agent.socket"}}

    # `before_update` hook actions ---
    def _release_display_manager_alias(self) -> None:
        alias = "/etc/systemd/system/display-manager.service"
        if not os.path.islink(alias):
            return

        target_unit = os.path.basename(os.path.realpath(alias))
        if target_unit == "sddm.service":
            return

        # greetd and sddm both install Alias=display-manager.service. The systemd plugin enables new units
        # before it disables old ones, and systemctl enable leaves an existing alias in place. Disabling the
        # current greeter removes the alias and leaves that greeter running.
        print_info(f"Disabling {target_unit} so SDDM can own display-manager.service.")
        _ = engine.run(["systemctl", "disable", target_unit])

    # `after_update` hook actions ---
    def _update_limine_conf_settings(self) -> None:
        path = "/boot/limine.conf"
        settings: dict[str, str] = {"timeout": "3", "default_entry": "2"}

        with open(path, "r", encoding="utf-8") as f:
            lines: list[str] = f.readlines()

        new_lines, found = [], set()
        for line in lines:
            key = line.split(":", 1)[0].strip() if ":" in line else None
            if key in settings:
                found.add(key)
                line: str = f"{key}: {settings[key]}\n"
            new_lines.append(line)

        prefix: list[str] = [f"{k}: {v}\n" for k, v in settings.items() if k not in found]
        final_lines: list[str] = prefix + new_lines

        if final_lines != lines:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(final_lines)

            print_info("Updated Limine boot menu settings.")
