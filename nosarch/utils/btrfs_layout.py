import subprocess
from subprocess import CompletedProcess

# The subvolume NosArch expects to find mounted at each mount point. The installer creates them, NosArch does not.
EXPECTED_SUBVOLUMES: dict[str, str] = {
    "/": "@",
    "/home": "@home",
    "/var/log": "@log",
    "/var/cache/pacman/pkg": "@pkg",
    "/swap": "@swap",
    "/.snapshots": "@snapshots",
}


def verify() -> None:
    """Fail if the target system's Btrfs subvolumes are not the ones NosArch expects.

    Snapper stores snapshots in `/.snapshots` and the swapfile lives in `/swap`. Each has to be a subvolume of its own,
    mounted there, rather than a directory or a subvolume nested in `@`: a rollback of `@` would take nested snapshots
    with it, and a subvolume holding an active swapfile cannot be snapshotted. A root that is not Btrfs is left alone.
    """
    if _mounted_filesystem("/") != "btrfs":
        return

    problems: list[str] = []
    for mount_point, expected in EXPECTED_SUBVOLUMES.items():
        found: str | None = _mounted_subvolume(mount_point)
        if found != expected:
            problems.append(f"{mount_point}: expected subvolume {expected}, found {found or 'nothing mounted'}")

    if problems:
        details: str = "\n".join(f"    {problem}" for problem in problems)
        raise RuntimeError(f"The Btrfs subvolumes are not the ones NosArch expects:\n{details}")


def _mounted_filesystem(mount_point: str) -> str | None:
    result: CompletedProcess[str] = _findmnt(mount_point, "FSTYPE")
    return result.stdout.strip() or None if result.returncode == 0 else None


def _mounted_subvolume(mount_point: str) -> str | None:
    """Return the name of the Btrfs subvolume mounted exactly at `mount_point`, or None if there is none."""
    result: CompletedProcess[str] = _findmnt(mount_point, "FSTYPE,OPTIONS")
    if result.returncode != 0:
        return None

    filesystem, _, options = result.stdout.strip().partition(" ")
    if filesystem != "btrfs":
        return None

    for option in options.split(","):
        if option.startswith("subvol="):
            return option.removeprefix("subvol=").lstrip("/")

    return None


def _findmnt(mount_point: str, columns: str) -> CompletedProcess[str]:
    # `--mountpoint` matches only a mount point itself. `--target` would answer for the filesystem containing the path,
    # so an unmounted `/swap` would report the root subvolume.
    return subprocess.run(
        ["findmnt", "--noheadings", "--first-only", "--output", columns, "--mountpoint", mount_point],
        capture_output=True,
        text=True,
        check=False,
    )
