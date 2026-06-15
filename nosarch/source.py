import decman.config
from config import CONFIG
from decman.extras.users import User, UserManager
from modules.desktop import DesktopModule
from modules.dev import DevModule
from modules.setup import SetupModule
from modules.system import SystemModule
from modules.theme import ThemingModule

# Decman configuration
decman.config.arch = "x86_64"
decman.config.debug_output = False  # Enable debug output
decman.config.quiet_output = False  # Disable info messages
decman.execution_order = [
    "files",
    "pacman",
    # "aur",
    "flatpak",
    "systemd",
]
# ---

# User and Group management
userManager: UserManager = UserManager()

userManager.add_user(
    User(
        username=CONFIG["%USER%"],
        group=CONFIG["%USER%"],
        home=f"/home/{CONFIG['%USER%']}",
        shell="/usr/bin/bash",
        groups=(
            CONFIG["%USER%"],
            "wheel",  # To make user an admin
            "libvirt",  # For virtualization
        ),
        system=False,
    )
)
# ---

decman.aur.packages |= {"decman"}
decman.aur.ignored_packages |= {"yay"}

decman.modules += {
    SystemModule(),
    DesktopModule(),
    ThemingModule(),
    SetupModule(),
    DevModule(),
}
