import decman
from decman.plugins import pacman


class FlatpakModule(decman.Module):
    """
    Installs the Flatpak runtime and prepares what the `flatpak` plugin drives.

    A module of its own because Flatpak needs more than a package: the runtime leaves every app's data on disk when it
    goes, so switching Flatpak off has to offer to clean that up.
    """

    def __init__(self) -> None:
        super().__init__(name="flatpak")

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_runtime(self) -> set[str]:
        return {"flatpak"}

    # Runs before the pacman step, so the runtime is still installed and can uninstall the apps itself.
    @staticmethod
    def on_disable() -> None:
        import os
        import shutil
        import sys
        from pathlib import Path

        import decman
        import decman.core.output

        # The config's username is not reachable from here: decman lifts this function's source into a
        # standalone script that can only use builtins and what it imports itself.
        username: str = os.environ.get("SUDO_USER", "root")

        # Uninstall with Flatpak first so it drops its own runtimes and export entries before the directories go.
        # `check=False` because anything this fails to remove is still deleted by path below.
        if shutil.which("flatpak") is not None:
            _ = decman.prg(["flatpak", "uninstall", "--all", "--system"], check=False)
            _ = decman.prg(["flatpak", "uninstall", "--all", "--user"], user=username, mimic_login=True, check=False)

        # Manually clean up everything that Flatpak did not remove ---
        home: Path = Path("/home") / username
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

        decman.core.output.print_warning("Flatpak is disabled, but its data is still on disk:")
        decman.core.output.print_list("These paths can be deleted:", [str(p) for p in present], 1)
        if dangling:
            decman.core.output.print_list(
                "These desktop entries point into the paths above:", [str(p) for p in dangling], 1
            )
        decman.core.output.print_warning(
            "Deleting them also deletes every Flatpak app's settings and data. This cannot be undone."
        )

        if not sys.stdin.isatty():
            # Nothing was asked, so leave the data.
            return

        if not decman.core.output.prompt_confirm("Delete all Flatpak data?", default=False):
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

        decman.core.output.print_info("Deleted Flatpak data.")
