import decman.config
from config import CONFIG
from decman.extras.users import User, UserManager
from modules.desktop import DesktopModule
from modules.setup import SetupModule
from modules.setup_full import FullSetupModule
from modules.system import SystemModule
from modules.theme import ThemingModule
from modules.usage_profiles.creative import CreativeModule
from modules.usage_profiles.dev import DevModule
from modules.usage_profiles.gaming import GamingModule

# Decman configuration
decman.config.arch = "x86_64"
decman.config.debug_output = False
decman.config.quiet_output = False  # Disable info messages
decman.execution_order = [
    "files",
    "pacman",
    # "aur",  Disabled due to recent npm supply chain attacks
    "flatpak",
    "systemd",
]

decman.aur.ignored_packages |= {"yay"}

# Ignored because needed for testing, not for user setups
decman.pacman.ignored_packages |= {"icon-library", "dconf-editor", "shellcheck"}
# ---

# User and Group management
userManager: UserManager = UserManager()

usergroups: list[str] = [
    CONFIG["%USER%"],
    "wheel",  # To make user an admin
    "libvirt",  # For virtualization
]

if CONFIG["%GAMING_PROFILE%"] == "true":
    usergroups.append("input")  # Allow user access to controller devices (/dev/input)

userManager.add_user(
    User(
        username=CONFIG["%USER%"],
        group=CONFIG["%USER%"],
        home=f"/home/{CONFIG['%USER%']}",
        shell="/usr/bin/bash",
        groups=tuple(usergroups),
        system=False,
    )
)
# ---

# Decman modules
decman.modules += {SystemModule(), DesktopModule(), ThemingModule(), SetupModule()}

if CONFIG["%FULL_SETUP%"] == "true":
    decman.modules += {FullSetupModule()}

if CONFIG["%CREATIVE_PROFILE%"] == "true":
    decman.modules += {CreativeModule()}

if CONFIG["%DEV_PROFILE%"] == "true":
    decman.modules += {DevModule()}

if CONFIG["%GAMING_PROFILE%"] == "true":
    decman.modules += {GamingModule()}
# ---
