import subprocess
from subprocess import CompletedProcess

SWAPFILE_PATH: str = "/swap/swapfile"


def get_resume_offset() -> str:
    """Return the physical offset of the Btrfs swapfile, for the `resume_offset` kernel parameter."""
    try:
        result: CompletedProcess[str] = subprocess.run(
            ["btrfs", "inspect-internal", "map-swapfile", "--resume-offset", SWAPFILE_PATH],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Could not get resume offset of {SWAPFILE_PATH}: {error.stderr.strip()}") from error

    offset: str = result.stdout.strip()
    if not offset.isdigit():
        raise RuntimeError(f"Unexpected resume offset for {SWAPFILE_PATH}: {offset!r}")

    return offset
