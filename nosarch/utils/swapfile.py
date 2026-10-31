import math
import os
import subprocess
from subprocess import CompletedProcess

SWAP_DIR: str = "/swap"
SWAPFILE_PATH: str = f"{SWAP_DIR}/swapfile"
HEADROOM_GIB: int = 2  # Beyond RAM, so the file also has room for ordinary swapping


def exists() -> bool:
    return os.path.exists(SWAPFILE_PATH)


def create() -> None:
    """Create the swapfile if it does not exist, sized to hold RAM plus headroom so hibernation can write it all out.

    The file lives in its own subvolume. A subvolume that holds an active swapfile cannot be snapshotted, and a nested
    subvolume is skipped when its parent is, so snapshots of the root subvolume keep working.
    """
    if exists():
        return

    root_fstype: str = _run(["findmnt", "--noheadings", "--output", "FSTYPE", "--target", "/"])
    if root_fstype != "btrfs":
        raise RuntimeError(f"A swapfile is only created on Btrfs. The root filesystem is: {root_fstype}")

    if not os.path.exists(SWAP_DIR):
        _ = _run(["btrfs", "subvolume", "create", SWAP_DIR])

    _ = _run(["btrfs", "filesystem", "mkswapfile", "--size", f"{_ram_gib() + HEADROOM_GIB}G", SWAPFILE_PATH])


def get_resume_offset() -> str:
    """Return the physical offset of the swapfile, for the `resume_offset` kernel parameter."""
    offset: str = _run(["btrfs", "inspect-internal", "map-swapfile", "--resume-offset", SWAPFILE_PATH])
    if not offset.isdigit():
        raise RuntimeError(f"Unexpected resume offset for {SWAPFILE_PATH}: {offset!r}")

    return offset


def _ram_gib() -> int:
    with open("/proc/meminfo", "r", encoding="utf-8") as meminfo:
        for line in meminfo:
            if line.startswith("MemTotal:"):
                return math.ceil(int(line.split()[1]) / (1024 * 1024))  # The value is in KiB

    raise RuntimeError("MemTotal not found in /proc/meminfo")


def _run(command: list[str]) -> str:
    try:
        result: CompletedProcess[str] = subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"`{' '.join(command)}` failed: {error.stderr.strip()}") from error

    return result.stdout.strip()
