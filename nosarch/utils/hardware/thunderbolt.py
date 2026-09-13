from pathlib import Path

THUNDERBOLT_DEVICES: Path = Path("/sys/bus/thunderbolt/devices")


def is_thunderbolt_present() -> bool:
    """
    Whether a Thunderbolt/USB4 controller is present.

    The `thunderbolt` module loads on any machine whose chipset exposes USB4
    (it is pulled in by `typec`), so module presence alone is not a signal.
    A real controller registers a `domainN` entry on the bus; hosts, retimers
    and connected devices then hang off that domain.
    """
    if not THUNDERBOLT_DEVICES.is_dir():
        return False

    return any(entry.name.startswith("domain") for entry in THUNDERBOLT_DEVICES.iterdir())
