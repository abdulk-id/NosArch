import subprocess
from subprocess import CompletedProcess


def get_luks_uuid() -> str:
    result: CompletedProcess[str] = subprocess.run(
        ["lsblk", "--raw", "--noheadings", "--output", "UUID,FSTYPE"], capture_output=True, text=True, check=True
    )

    luks_uuids: list[str] = [
        line.split()[0]
        for line in result.stdout.splitlines()
        if len(line.split()) == 2 and line.split()[1] == "crypto_LUKS"
    ]

    if len(luks_uuids) != 1:
        raise RuntimeError(f"One LUKS container expected. Found: {len(luks_uuids)}")

    return luks_uuids[0]
