"""
Flatpak leaves its data on disk after the runtime package is removed. This utility offer to delete it.

Called from `source.py` before pacman runs, so the runtime is still installed and can uninstall the apps itself.
Whatever it leaves behind, including app data in `~/.var/app` that `flatpak uninstall` never touches, is removed by path.
"""

import os
import shutil
import sys
from pathlib import Path

import decman
import decman.core.output

# The system install, which also holds the app data of system-wide apps.
SYSTEM_DIR: Path = Path("/var/lib/flatpak")


def _get_data_paths(username: str) -> list[Path]:
    """
    Returns the paths that hold Flatpak state.

    Paths that don't exist are left in and callers decide what to do about them.
    """
    home: Path = Path("/home") / username

    return [
        SYSTEM_DIR,
        home / ".local/share/flatpak",  # Per-user install
        home / ".var/app",  # Per-user app data
    ]


def _get_dangling_desktop_files(username: str) -> list[Path]:
    """
    Returns per-user `.desktop` symlinks that point into Flatpak's export dirs.

    Flatpak apps register themselves by symlinking into `exports/share/applications`. Deleting the Flatpak data leaves
    those links broken.
    """
    apps_dir: Path = Path("/home") / username / ".local/share/applications"
    export_dirs: tuple[str, ...] = (
        str(SYSTEM_DIR / "exports"),
        str(Path("/home") / username / ".local/share/flatpak/exports"),
    )

    if not apps_dir.is_dir():
        return []

    dangling: list[Path] = []
    for entry in sorted(apps_dir.iterdir()):
        if not entry.is_symlink():
            continue

        target: str = os.readlink(entry)
        if not target.startswith(export_dirs):
            continue

        # A link can still resolve if only part of the path was removed, so check the target itself.
        if not entry.exists():
            dangling.append(entry)

    return dangling


def _remove(paths: list[Path]) -> None:
    """
    Deletes the given files and directories, ignoring ones that are already gone.
    """
    for path in paths:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def _uninstall_apps(username: str) -> None:
    """
    Uninstalls every system-wide and per-user app, so Flatpak drops its own runtimes and export
    entries before the directories go.

    Runs with `check=False` because anything it fails to remove is still deleted by path afterwards.
    """
    if shutil.which("flatpak") is None:
        return

    decman.prg(["flatpak", "uninstall", "--all", "--system"], check=False)
    decman.prg(["flatpak", "uninstall", "--all", "--user"], user=username, mimic_login=True, check=False)


def offer_cleanup(username: str, dry_run: bool) -> None:
    """
    Offers to delete Flatpak's data, on the run where the runtime is being removed.

    Whether this is that run is decided by the runtime still being installed. Pacman removes it later in the same run,
    so every run after that finds it gone and stays quiet. That also means the offer comes back on its own if Flatpak
    is re-enabled and disabled again, with no state to remember and nothing that can drift out of sync with reality.

    `~/.var/app` holds app settings and game saves that exist nowhere else, so this asks and defaults to no.
    """
    if shutil.which("flatpak") is None:
        # The runtime is already gone, so this is not the run that removes it.
        return

    data_paths: list[Path] = [p for p in _get_data_paths(username) if p.exists()]
    dangling_files: list[Path] = _get_dangling_desktop_files(username)

    if not data_paths and not dangling_files:
        return

    decman.core.output.print_warning("Flatpak is disabled, but its data is still on disk:")
    decman.core.output.print_list("These paths can be deleted:", [str(p) for p in data_paths], 1)
    if dangling_files:
        decman.core.output.print_list(
            "These desktop entries point into the paths above:", [str(p) for p in dangling_files], 1
        )
    decman.core.output.print_warning(
        "Deleting them also deletes every Flatpak app's settings and data. This cannot be undone."
    )

    if dry_run:
        decman.core.output.print_info("Dry run, leaving the data alone.")
        return

    if not sys.stdin.isatty():
        # Nothing was asked, so the offer stays open for the next interactive run.
        return

    if not decman.core.output.prompt_confirm("Delete all Flatpak data?", default=False):
        return

    _uninstall_apps(username)

    # Uninstalling removes the export dirs, so the desktop entries have to be looked up again.
    _remove(data_paths)
    _remove(_get_dangling_desktop_files(username))
    decman.core.output.print_info("Deleted Flatpak data.")
