import subprocess
import sys

import decman.config
import user_config.config_reader as userConfig
import utils.aur_chroot
from decman.extras.users import User, UserManager
from modules.desktop import DesktopModule
from modules.homebrew import HomebrewModule
from modules.setup import SetupModule
from modules.setup_full import FullSetupModule
from modules.system import SystemModule
from modules.theme import ThemingModule
from modules.usage_profiles.creative import CreativeModule
from modules.usage_profiles.dev import DevModule
from modules.usage_profiles.gaming import GamingModule
from modules.user_defined import UserDefinedModule
from plugins import homebrew

# Checks ===

# decman does not import this file, it reads it as text and `exec()`s it after `os.chdir`-ing into its directory,
# so `__file__` here would resolve to decman's own module rather than this one.
_path_check: subprocess.CompletedProcess[bytes] = subprocess.run([sys.executable, "../tools/check_paths.py"])

if _path_check.returncode != 0:
    raise SystemExit("[CHECKS] ABORT: Dangling path references found in dotfiles.")
# ===

userConfig.load()
_username: str = userConfig.get_str("user.username")

# Decman configuration ===
decman.config.arch = "x86_64"
decman.config.debug_output = False
decman.config.quiet_output = False  # Disable info messages
decman.execution_order = ["files", "pacman", "aur", "flatpak", "systemd"]

# decman builds in /tmp by default, which is a tmpfs. Build on disk instead
decman.aur.build_dir = "/var/cache/decman/build"

if utils.aur_chroot.is_available():
    # NosArch's own pacman hooks must not apply to the AUR build chroot: `mkarchroot`
    # evaluates host hooks against an empty root, where no `Depends =` can be
    # satisfied, which aborts the build before anything is installed.
    decman.aur.commands = utils.aur_chroot.NoHostHooksAurCommands()

if userConfig.get_bool("enable_homebrew"):
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
        + (("libvirt",) if userConfig.get_bool("full_setup.enable_virtualization") else ())
        + (
            ("input",) if userConfig.get_bool("profiles.gaming") else ()
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
decman.modules += {SystemModule(), DesktopModule(), ThemingModule(), SetupModule()}

if userConfig.get_bool("enable_homebrew"):
    decman.modules += {HomebrewModule()}

desktop_enabled: bool = any(module.name == "desktop" for module in decman.modules)

if userConfig.get_bool("profiles.full_setup"):
    if desktop_enabled:
        decman.modules += {FullSetupModule()}
    else:
        raise SystemExit("[CHECKS] ABORT: Creative profile requires Desktop module to be enabled.")

if userConfig.get_bool("profiles.creative"):
    if desktop_enabled:
        decman.modules += {CreativeModule()}
    else:
        raise SystemExit("[CHECKS] ABORT: Creative profile requires Desktop module to be enabled.")

if userConfig.get_bool("profiles.dev"):
    if desktop_enabled:
        decman.modules += {DevModule()}
    else:
        # Task for later: Make dev module workable without desktop
        raise SystemExit("[CHECKS] ABORT: Creative profile requires Desktop module to be enabled.")

if userConfig.get_bool("profiles.gaming"):
    if desktop_enabled:
        decman.modules += {GamingModule()}
    else:
        raise SystemExit("[CHECKS] ABORT: Creative profile requires Desktop module to be enabled.")

decman.modules += {UserDefinedModule()}
# ===
