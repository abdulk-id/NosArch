from collections.abc import Callable

import nosarch.engine.setup
from nosarch.engine.steps import aur, files, flatpak, homebrew, pacman, snap, systemd, users

STEPS: dict[str, Callable[[nosarch.engine.setup.Context], None]] = {
    "users": users.run,
    "files": files.run,
    "pacman": pacman.run,
    "aur": aur.run,
    "systemd": systemd.run,
    "flatpak": flatpak.run,
    "homebrew": homebrew.run,
    "snap": snap.run,
}

KINDS: dict[str, tuple[str, ...]] = {
    "pacman": ("pacman",),
    "aur": ("aur", "custom"),
    "systemd": ("systemd", "systemd_user"),
    "flatpak": ("flatpak", "flatpak_user"),
    "homebrew": ("brew_formula", "brew_cask", "brew_tap"),
    "snap": ("snap", "snap_classic"),
}
