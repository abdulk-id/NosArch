import os
import subprocess
from subprocess import CompletedProcess

SNAPSHOTS_DIR: str = "/.snapshots"


def create_subvolume() -> None:
    """Create the Btrfs subvolume snapper stores root snapshots in, if it does not exist.

    `snapper create-config` normally does this, but NosArch writes snapper's config itself, so nothing else would.
    Snapper fails with `open failed path://.snapshots` without it. The package backup pacman hook runs in the first
    pacman transaction, so this has to happen before that step. A root that is not Btrfs is left alone, because snapper
    cannot take snapshots there either.
    """
    if os.path.exists(SNAPSHOTS_DIR):
        return

    if _run(["findmnt", "--noheadings", "--output", "FSTYPE", "--target", "/"]) != "btrfs":
        return

    _ = _run(["btrfs", "subvolume", "create", SNAPSHOTS_DIR])
    os.chmod(SNAPSHOTS_DIR, 0o750)


def _run(command: list[str]) -> str:
    try:
        result: CompletedProcess[str] = subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"`{' '.join(command)}` failed: {error.stderr.strip()}") from error

    return result.stdout.strip()
