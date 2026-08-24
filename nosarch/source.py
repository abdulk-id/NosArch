import decman.config
import user_config.config_reader as userConfig
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
from plugins import homebrew

userConfig.load()
_username: str = userConfig.get_str("user.username")

# Decman configuration
decman.config.arch = "x86_64"
decman.config.debug_output = False
decman.config.quiet_output = False  # Disable info messages
decman.execution_order = ["files", "pacman", "aur", "flatpak", "systemd"]

if userConfig.get_bool("enable_homebrew"):
    homebrew.plugin.user = _username  # brew cannot run as root
    decman.plugins["homebrew"] = homebrew.plugin
    decman.execution_order.insert(decman.execution_order.index("systemd"), "homebrew")

decman.aur.ignored_packages |= {"yay"}

# Ignored because needed for testing, not for user setups
decman.pacman.ignored_packages |= {"icon-library", "dconf-editor", "shellcheck"}
# ---

# User and Group management
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
# ---

# Decman modules
decman.modules += {SystemModule(), DesktopModule(), ThemingModule(), SetupModule()}

if userConfig.get_bool("enable_homebrew"):
    decman.modules += {HomebrewModule()}

if userConfig.get_bool("profiles.full_setup"):
    decman.modules += {FullSetupModule()}

if userConfig.get_bool("profiles.creative"):
    decman.modules += {CreativeModule()}

if userConfig.get_bool("profiles.dev"):
    decman.modules += {DevModule()}

if userConfig.get_bool("profiles.gaming"):
    decman.modules += {GamingModule()}
# ---
