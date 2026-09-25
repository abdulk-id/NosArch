import os
import subprocess
import sys

import decman.config
import decman.core.output
import utils.aur_chroot
from decman.extras.users import User, UserManager
from modules.desktop import DesktopModule
from modules.homebrew import HomebrewModule
from modules.setup import SetupModule
from modules.system import SystemModule
from modules.theme import ThemingModule
from modules.usage_profiles.ai import AIModule
from modules.usage_profiles.creative import CreativeModule
from modules.usage_profiles.dev import DevModule
from modules.usage_profiles.gaming import GamingModule
from modules.user_defined import UserDefinedModule
from plugins import homebrew
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

        # decman does not import this file, it reads it as text and `exec()`s it after `os.chdir`-ing into its directory,
        # so `__file__` here would resolve to decman's own module rather than this one.
        _path_check: subprocess.CompletedProcess[bytes] = subprocess.run([sys.executable, "../tools/check_paths.py"])
        if _path_check.returncode != 0:
            decman.core.output.print_error("[CHECKS] Dangling path references found in dotfiles.")
            raise SystemExit()

        _custom_package_check: subprocess.CompletedProcess[bytes] = subprocess.run(
            [sys.executable, "../tools/check_custom_packages.py"]
        )
        if _custom_package_check.returncode == 1:
            decman.core.output.print_error("[CHECKS] Custom package check failed with error(s).")
            raise SystemExit()
        elif _custom_package_check.returncode == 2:
            decman.core.output.print_warning("[CHECKS] Custom package check has unresolved warnings.")
else:
    decman.config.debug_output = False
    decman.config.quiet_output = True  # Disable info messages
# ===

# Decman configuration ===
decman.config.arch = "x86_64"
decman.execution_order = ["files", "pacman", "aur", "flatpak", "systemd"]

# decman builds in /tmp by default, which is a tmpfs. Build on disk instead
decman.aur.build_dir = "/var/cache/decman/build"

if utils.aur_chroot.is_available():
    # NosArch's own pacman hooks must not apply to the AUR build chroot. `mkarchroot` evaluates host hooks against an
    # empty root, where no `Depends =` can be satisfied, which aborts the build.
    decman.aur.commands = utils.aur_chroot.NoHostHooksAurCommands()

if user_config.get_bool("enable_homebrew"):
    homebrew.plugin.user = _username  # brew cannot run as root
    decman.plugins["homebrew"] = homebrew.plugin
    decman.execution_order.insert(decman.execution_order.index("systemd"), "homebrew")
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
        # TODO: Only show error if desktop apps for AI are enabled
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
