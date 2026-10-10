import os
import subprocess
import sys

import decman.config
import decman.core.output
import utils.aur_chroot
from decman.extras.users import User, UserManager
from decman.plugins import flatpak as flatpak_plugin
from modules.desktop import DesktopModule
from modules.flatpak import FlatpakModule
from modules.homebrew import HomebrewModule
from modules.setup import SetupModule
from modules.snap import SnapModule
from modules.system import SystemModule
from modules.theme import ThemingModule
from modules.usage_profiles.ai import AIModule
from modules.usage_profiles.creative import CreativeModule
from modules.usage_profiles.dev import DevModule
from modules.usage_profiles.gaming import GamingModule
from modules.user_defined import UserDefinedModule
from plugins import homebrew
from plugins import snap as snap_plugin
from utils.user_config_reader import UserConfigReader

# User config
user_config: UserConfigReader = UserConfigReader()
_username: str = user_config.get_str("user.username")

# NosArch Works ===
if user_config.get_bool("advanced.enable_nosarch_works"):
    # decman.config.debug_output = True
    decman.config.quiet_output = False

    # Machine setup ---
    decman.pacman.packages |= {"lynis", "namcap", "pacman-contrib", "shellcheck"}

    # Checks ---
    DISABLE_CHECKS_PARAM: bool = os.environ.get("NOSARCH_DECMAN_SKIP_CHECKS") == "1"

    if DISABLE_CHECKS_PARAM:
        decman.core.output.print_warning("Skipping NosArch pre-checks.")
    else:
        decman.core.output.print_summary("Running NosArch pre-checks.")

        # Many custom packages = check takes time. Give option (to allow skipping just this check for quick dry-runs)
        if decman.core.output.prompt_confirm("Run Custom package check?", True):
            _custom_package_check: subprocess.CompletedProcess[bytes] = subprocess.run(
                [sys.executable, "../tools/manage_custom_packages.py", "refresh"]
            )
            if _custom_package_check.returncode == 1:
                decman.core.output.print_error("[CHECKS] Custom package check failed with error(s).")
                raise SystemExit()
            elif _custom_package_check.returncode == 2:
                decman.core.output.print_warning("[CHECKS] Custom package check has unresolved warnings.")
        else:
            decman.core.output.print_warning("[CHECKS] Custom package check manually skipped for this run.")
else:
    decman.config.debug_output = False
    decman.config.quiet_output = True  # Disable info messages
# ===

# Decman configuration ===
decman.config.arch = "x86_64"
decman.execution_order = ["files", "pacman", "aur", "systemd"]

decman.aur.build_dir = "/var/cache/decman/build"

if utils.aur_chroot.is_available():
    # NosArch's own pacman hooks must not apply to the AUR build chroot. `mkarchroot` evaluates host hooks against an
    # empty root, where no `Depends =` can be satisfied, which aborts the build.
    decman.aur.commands = utils.aur_chroot.NoHostHooksAurCommands()
# ===

# Packaging ===
if user_config.get_bool("packaging.flatpak"):
    # Register the plugin here manually. decman only consults a plugin's `available()` when it is imported, which
    # happens before pacman installs the runtime, so on the run that enables Flatpak the plugin isn't registered yet
    # and its step would be skipped.
    if "flatpak" not in decman.plugins:
        decman.plugins["flatpak"] = flatpak_plugin.Flatpak()

    decman.execution_order.append("flatpak")
else:
    # Dropping the module is what runs `FlatpakModule.on_disable`, which offers to delete what the runtime
    # left behind. It cannot be driven from here: decman only runs that script when a registered module
    # disappears.
    _skipped_flatpak: list[str] = user_config.get_str_list("user_packages.flatpak") + user_config.get_str_list(
        "user_packages.flatpak_user"
    )
    if _skipped_flatpak:
        decman.core.output.print_warning("[PACKAGING] Flatpak is disabled. Ignoring user packages")


if user_config.get_bool("enable_homebrew"):
    homebrew.plugin.user = _username  # brew cannot run as root
    decman.plugins["homebrew"] = homebrew.plugin
    decman.execution_order.append("homebrew")


if user_config.get_bool("packaging.snap"):
    # Registered here directly rather than left to `available()`, which decman only consults when it
    # imports a plugin. That happens before the AUR step installs snapd, so on the run that enables
    # Snap the plugin isn't registered yet and its step would be skipped. The plugin reports a missing
    # `snap` itself, which is what a dry run of that first run will see.
    decman.plugins["snap"] = snap_plugin.plugin
    decman.execution_order.append("snap")
else:
    # Dropping the module is what runs `SnapModule.on_disable`, which offers to delete what snap
    # left behind. It cannot be driven from here: decman only runs that script when a registered
    # module disappears.
    _skipped_snaps: dict[str, str] = user_config.get_str_dict("user_packages.snap")
    _skipped_snaps |= user_config.get_str_dict("user_packages.classic_snap")
    if _skipped_snaps:
        decman.core.output.print_warning("[PACKAGING] Snap is disabled. Ignoring user packages")
# ===

# User and Group management ===
userManager: UserManager = UserManager()

userManager.add_user(
    User(
        username=_username,
        group=_username,
        home=f"/home/{_username}",
        shell="/usr/bin/bash",
        groups=(_username, "wheel")
        + (("libvirt",) if user_config.get_bool("setup.enable_virtualization") else ())
        + (
            ("input",) if user_config.get_bool("profiles.gaming") else ()
            # Allow user access to controller devices (/dev/input)
        ),
        system=False,
    )
)

userManager.add_user(User(username="aurbuilduser", home="/var/lib/aurbuilduser", system=True))
decman.aur.makepkg_user = "aurbuilduser"

decman.modules += {userManager}
# ===

# Decman modules ===
decman.modules += {SystemModule(user_config), DesktopModule(user_config), ThemingModule(user_config)}

if user_config.get_bool("enable_homebrew"):
    decman.modules += {HomebrewModule(_username)}

if user_config.get_bool("packaging.flatpak"):
    decman.modules += {FlatpakModule()}

if user_config.get_bool("packaging.snap"):
    decman.modules += {SnapModule()}

desktop_enabled: bool = any(module.name == "desktop" for module in decman.modules)

if user_config.get_bool("profiles.setup"):
    if desktop_enabled:
        decman.modules += {SetupModule(user_config)}
    else:
        decman.core.output.print_error("[PROFILES] Setup module requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.get_bool("profiles.ai"):
    if desktop_enabled:
        decman.modules += {AIModule(user_config)}
    else:
        decman.core.output.print_error("[PROFILES] AI module requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.get_bool("profiles.creative"):
    if desktop_enabled:
        decman.modules += {CreativeModule(user_config)}
    else:
        decman.core.output.print_error("[PROFILES] Creative profile requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.get_bool("profiles.dev"):
    if desktop_enabled:
        decman.modules += {DevModule(user_config)}
    else:
        decman.core.output.print_error("[PROFILES] Dev profile requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.get_bool("profiles.gaming"):
    if desktop_enabled:
        decman.modules += {GamingModule(user_config)}
    else:
        decman.core.output.print_error("[PROFILES] Gaming profile requires Desktop module to be enabled.")
        raise SystemExit()

decman.modules += {UserDefinedModule(user_config)}
# ===
