"""
Keeps NosArch's own pacman hooks out of decman's AUR build chroot.

`mkarchroot` installs into an empty root using the *host* pacman
configuration, so every hook in `/etc/pacman.d/hooks/` is evaluated against
that empty root. A hook with `Depends =` can never be satisfied there
(nothing is installed yet), and a `PreTransaction` hook with `AbortOnFail`
then takes the whole build down before a single package is written.

Package-provided hooks under `/usr/share/libalpm/hooks/` are unaffected:
pacman always reads that directory, and those hooks are what the chroot
actually needs.
"""

import os
import shutil
from typing import override

from decman.plugins.aur import AurCommands

PACMAN_CONF: str = "/etc/pacman.conf"

# Somewhere to point pacman at that is guaranteed to contain no hooks.
EMPTY_HOOK_DIR: str = "/tmp/decman/nosarch-empty-hooks"
CHROOT_PACMAN_CONF: str = "/tmp/decman/nosarch-chroot-pacman.conf"


def chroot_pacman_conf() -> str:
    """
    Writes a copy of the host pacman config whose only `HookDir` is empty,
    and returns its path.
    """
    os.makedirs(EMPTY_HOOK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CHROOT_PACMAN_CONF), exist_ok=True)

    lines: list[str] = []
    inserted: bool = False

    with open(PACMAN_CONF, encoding="utf-8") as conf:
        for line in conf:
            stripped: str = line.strip()

            # Drop any HookDir the host sets; ours is the only one that applies.
            if stripped.startswith("HookDir"):
                continue

            lines.append(line)

            if not inserted and stripped == "[options]":
                lines.append(f"HookDir = {EMPTY_HOOK_DIR}/\n")
                inserted = True

    if not inserted:
        raise SystemExit(f"[CHECKS] ABORT: No [options] section in {PACMAN_CONF}.")

    with open(CHROOT_PACMAN_CONF, "w", encoding="utf-8") as conf:
        conf.writelines(lines)

    return CHROOT_PACMAN_CONF


class NoHostHooksAurCommands(AurCommands):
    """`AurCommands` that builds the chroot without the host's own hooks."""

    @override
    def make_chroot(self, chroot_dir: str, with_pkgs: set[str]) -> list[str]:
        return ["mkarchroot", "-C", chroot_pacman_conf(), chroot_dir] + list(with_pkgs)


def is_available() -> bool:
    """Whether the tooling this override assumes is actually present."""
    return shutil.which("mkarchroot") is not None and os.path.isfile(PACMAN_CONF)
