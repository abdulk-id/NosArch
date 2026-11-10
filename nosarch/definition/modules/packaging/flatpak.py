import os
import shutil
from pathlib import Path
from typing import override

import engine
import engine.output
import utils.paths
from engine import File
from engine.steps import pacman

# The .flatpakrepo file is Flathub's remote description. Kept in step with the pacman hook
# at /etc/pacman.d/hooks/10-flatpak-flathub.hook, which runs the same command.
_FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"


class FlatpakModule(engine.Module):
    """
    Installs the Flatpak runtime and prepares what the `flatpak` step drives.

    A module of its own because Flatpak needs more than a package: the runtime leaves every app's data on disk when it
    goes, so switching Flatpak off has to offer to clean that up. Enabling it also adds the Flathub remote, which is
    what install and search look at.
    """

    def __init__(self, username: str) -> None:
        super().__init__(name="flatpak")
        self._username: str = username

    @override
    def files(self) -> dict[str, File]:
        # nosarch-package sources the library when it exists and skips Flatpak when it does not, which is how the CLI
        # follows this module being enabled or disabled. The hook adds Flathub on the run that installs flatpak.
        return utils.paths.Dotfiles("../dotfiles/system-root").files(
            "/usr/local/bin/util/package/flatpak.sh", "/etc/pacman.d/hooks/10-flatpak-flathub.hook"
        )

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_runtime(self) -> set[str]:
        return {"flatpak"}

    @override
    def before_update(self) -> None:
        # before_update runs before pacman, so the run that first installs flatpak has no binary yet. The hook
        # covers that run. This covers every later run, and a machine where flatpak was already installed.
        if shutil.which("flatpak") is None:
            return

        _ = engine.run(["flatpak", "remote-add", "--if-not-exists", "--system", "flathub", _FLATHUB_REPO])

    # Runs before the pacman step, so the runtime is still installed and can uninstall the apps itself.
    @override
    def on_disable(self) -> None:
        # Uninstall with Flatpak first so it drops its own runtimes and export entries before the directories go.
        # `check=False` because anything this fails to remove is still deleted by path below.
        if shutil.which("flatpak") is not None:
            _ = engine.run(["flatpak", "uninstall", "--all", "--system"], check=False)
            _ = engine.run(["flatpak", "uninstall", "--all", "--user"], user=self._username, check=False)

        # Manually clean up everything that Flatpak did not remove ---
        home: Path = Path("/home") / self._username
        system_dir: Path = Path("/var/lib/flatpak")
        apps_dir: Path = home / ".local/share/applications"

        data_paths: list[Path] = [
            system_dir,  # The system install, which also holds system-wide app data
            home / ".local/share/flatpak",  # Per-user install
            home / ".var/app",  # Per-user app data, which `flatpak uninstall` never touches
        ]
        export_dirs: tuple[str, ...] = (str(system_dir / "exports"), str(home / ".local/share/flatpak/exports"))

        # Flatpak apps register themselves by symlinking into `exports/share/applications`, so deleting the data
        # leaves those links broken. Both the uninstall above and the deletion below remove the export dirs but
        # not the links, so whether a link is broken is only settled afterwards. Gather the candidates once here
        # and test them at the point of use, rather than walking the directory again after the teardown.
        candidates: list[Path] = []
        if apps_dir.is_dir():
            for entry in sorted(apps_dir.iterdir()):
                if not entry.is_symlink():
                    continue
                # A link can still resolve if only part of the path was removed, so the target itself is checked.
                if os.readlink(entry).startswith(export_dirs):
                    candidates.append(entry)

        present: list[Path] = [p for p in data_paths if p.exists()]
        dangling: list[Path] = [c for c in candidates if not c.exists()]

        if not present and not dangling:
            return

        engine.output.print_warning("Flatpak is disabled, but its data is still on disk:")
        engine.output.print_list("These paths can be deleted:", [str(p) for p in present], one_per_line=True)
        engine.output.print_list(
            "These desktop entries point into the paths above:", [str(p) for p in dangling], one_per_line=True
        )
        engine.output.print_warning(
            "Deleting them also deletes every Flatpak app's settings and data. This cannot be undone."
        )

        # Without a terminal nothing is asked, so the data stays.
        if not engine.output.prompt_confirm("Delete all Flatpak data?", default=False):
            return

        for path in present:
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

        # Tested again here, not above: links that resolved a moment ago are broken by what was just deleted,
        # and those are the ones worth reporting. Uninstalling leaves the links themselves in place, so the
        # candidates gathered earlier still hold and the directory does not need walking a second time.
        for entry in candidates:
            if entry.is_symlink() and not entry.exists():
                entry.unlink(missing_ok=True)

        engine.output.print_info("Deleted Flatpak data.")
