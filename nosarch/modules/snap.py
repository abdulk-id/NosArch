from typing import override

import decman
from decman import Symlink
from decman.plugins import aur, systemd


class SnapModule(decman.Module):
    """
    Installs snapd and prepares what the `snap` plugin drives.

    snapd comes from the AUR. `snapd.socket` launches the daemon when a snap command asks for it, and
    `snapd.apparmor.service` loads the AppArmor profiles that confine snaps.

    A module of its own, like Homebrew's, because Snap needs more than a package and a service: it also needs a link
    in place before a classic snap can install, and teardown when it is switched off.
    """

    def __init__(self) -> None:
        super().__init__(name="snap")

    @override
    def symlinks(self) -> dict[str, str | Symlink]:
        # Classic-confined snaps resolve their files under /snap, which snapd does not ship.
        #
        # Decman creates the link without checking that the target exists, so this is fine even on the run that
        # installs snapd: /var/lib/snapd/snap only appears once snapd does, and nothing reads /snap until the snap
        # step, which runs after. Disabling the module drops the declaration and decman removes the link.
        return {"/snap": "/var/lib/snapd/snap"}

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def snapd(self) -> set[str]:
        return {"snapd"}

    @systemd.units  # pyright: ignore[reportUnknownMemberType]
    def snap_services(self) -> set[str]:
        return {"snapd.socket", "snapd.apparmor.service"}

    # Runs before the AUR step, so snapd would still be installed.
    @staticmethod
    def on_disable() -> None:
        import os  # noqa: F811
        import shutil
        import sys
        from pathlib import Path

        import decman
        import decman.core.output

        userhome: Path = Path("/home") / os.environ.get("SUDO_USER", "root")

        paths: list[Path] = [
            Path("/var/lib/snapd"),  # The system install
            Path("/snap"),  # The link above, pointing into it
            userhome / "snap",  # Per-user app data, for system-wide snaps too
        ]
        present: list[Path] = [p for p in paths if p.exists() or p.is_symlink()]

        if not present:
            return

        decman.core.output.print_warning("Snap is disabled, but its data is still on disk.")
        decman.core.output.print_list("These paths can be deleted:", [str(p) for p in present], 1)
        decman.core.output.print_warning(
            "Deleting them also deletes every Snap app's settings and data. This cannot be undone."
        )

        if not sys.stdin.isatty():
            # Nothing was asked, so leave the data.
            return

        if not decman.core.output.prompt_confirm("Delete all Snap data?", default=False):
            return

        # Snapd holds squashfs mounts of its own. Stopping the socket tears the daemon down so the directories
        # underneath are not in use. There is no `snap remove --all`, so the snaps go with the directories.
        _ = decman.prg(["systemctl", "stop", "snapd.socket"], check=False)

        for path in present:
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

        decman.core.output.print_info("Deleted Snap data.")
