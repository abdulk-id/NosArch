from pathlib import Path

LAPTOP_CHASSIS: set[str] = {"8", "9", "10", "14", "30", "31", "32"}
# 8 - Portable
# 9 - Laptop
# 10 - Notebook
# 14 - Sub-Notebook (?)
# 30 - Tablet
# 31 - Convertible
# 32 - Detachable
# Source: https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.5.0.pdf
# More types: 5="pizza box", 16="lunch-box"


def is_laptop() -> bool:
    try:
        chassis: str = Path("/sys/class/dmi/id/chassis_type").read_text().strip()
        return chassis in LAPTOP_CHASSIS
    except FileNotFoundError:
        return False


def has_battery() -> bool:
    power_supplies: Path = Path("/sys/class/power_supply")
    if not power_supplies.exists():
        return False

    for device in power_supplies.iterdir():
        type_file: Path = device / "type"

        if not type_file.exists():
            continue

        if type_file.read_text().strip() == "Battery":
            return True

    return False
