"""The steps of a run, in the order `Setup.steps` lists them."""

from collections.abc import Callable

import engine.setup
from engine.steps import aur, files, flatpak, homebrew, pacman, snap, systemd, users

STEPS: dict[str, Callable[[engine.setup.Context], None]] = {
    "users": users.run,
    "files": files.run,
    "pacman": pacman.run,
    "aur": aur.run,
    "systemd": systemd.run,
    "flatpak": flatpak.run,
    "homebrew": homebrew.run,
    "snap": snap.run,
}

# The declaration kinds each step acts on. A kind is only diffed, and only counts as changed, when its step runs, so
# `--only files` never reports a package change it did not make.
KINDS: dict[str, tuple[str, ...]] = {
    "pacman": ("pacman",),
    "aur": ("aur", "custom"),
    "systemd": ("systemd", "systemd_user"),
    "flatpak": ("flatpak", "flatpak_user"),
    "homebrew": ("brew_formula", "brew_cask", "brew_tap"),
    "snap": ("snap", "snap_classic"),
}
