import decman.config

from desktop import DesktopModule
from dev import DevModule
from setup import SetupModule
from system import SystemModule

# Decman configuration
decman.config.arch = "x86_64"
decman.config.debug_output = False  # Enable debug output
decman.config.quiet_output = False  # Disable info messages
decman.execution_order = [
    "files",
    "pacman",
    "aur",
    "flatpak",
    "systemd",
]

decman.aur.packages |= {"decman"}
decman.aur.ignored_packages |= {"yay"}
# ---

decman.modules += {SystemModule(), DesktopModule(), SetupModule(), DevModule()}
