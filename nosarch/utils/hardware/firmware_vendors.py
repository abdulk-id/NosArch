from pathlib import Path

import utils.hardware.cpu_vendor

PCI_DEVICES: Path = Path("/sys/bus/pci/devices")
USB_DEVICES: Path = Path("/sys/bus/usb/devices")
MODULES: Path = Path("/proc/modules")

# Firmware packages installed regardless of what is detected.
#
# `linux-firmware-whence` is only licensing metadata and is a dependency of the
# vendor splits. `linux-firmware-other` holds firmware for devices that are not
# cleanly attributable to a PCI/USB vendor (keyboards, touch controllers, some
# webcams), so there is no reliable signal to gate it on.
ALWAYS_INSTALLED_FIRMWARE: set[str] = {"linux-firmware-other", "linux-firmware-whence"}

# Vendor firmware selected by PCI vendor ID.
#
# Device IDs are the trustworthy signal here. Module presence is not: `btusb`
# pulls in `btmtk`, `btrtl`, `btbcm` and `btintel` together on every machine
# with USB bluetooth, so a module-based check reports four vendors on hardware
# that only has one.
PCI_VENDOR_FIRMWARE: dict[str, str] = {
    "0x14e4": "linux-firmware-broadcom",  # Broadcom
    "0x1043": "linux-firmware-atheros",  # Atheros
    "0x168c": "linux-firmware-atheros",  # Qualcomm Atheros
    "0x17cb": "linux-firmware-atheros",  # Qualcomm
    "0x1969": "linux-firmware-atheros",  # Atheros (Killer)
    "0x14c3": "linux-firmware-mediatek",  # MediaTek
    "0x10ec": "linux-firmware-realtek",  # Realtek
    "0x8086": "linux-firmware-intel",  # Intel
    "0x1cf6": "linux-firmware-realtek",  # Realtek (rebranded)
}

# Vendor firmware selected by USB vendor ID.
USB_VENDOR_FIRMWARE: dict[str, str] = {
    "0a5c": "linux-firmware-broadcom",  # Broadcom
    "0489": "linux-firmware-mediatek",  # Foxconn/MediaTek combo modules
    "0e8d": "linux-firmware-mediatek",  # MediaTek
    "0bda": "linux-firmware-realtek",  # Realtek
    "0cf3": "linux-firmware-atheros",  # Qualcomm Atheros
    "8086": "linux-firmware-intel",  # Intel
    "8087": "linux-firmware-intel",  # Intel (bluetooth)
}

# GPU firmware selected by loaded kernel module.
#
# Unlike the bluetooth helpers, graphics modules only load when matching
# hardware is present, so this is a sound signal. `nvidia` is deliberately
# absent: the proprietary driver ships its own firmware, and
# `linux-firmware-nvidia` exists for nouveau.
MODULE_FIRMWARE: dict[str, str] = {
    "amdgpu": "linux-firmware-amdgpu",
    "radeon": "linux-firmware-radeon",
    "nouveau": "linux-firmware-nvidia",
    "snd_hda_scodec_cs35l41_i2c": "linux-firmware-cirrus",
    "snd_hda_scodec_cs35l41_spi": "linux-firmware-cirrus",
    "snd_soc_cs35l41": "linux-firmware-cirrus",
}


def get_pci_vendors() -> set[str]:
    if not PCI_DEVICES.is_dir():
        return set()

    vendors: set[str] = set()

    for device in PCI_DEVICES.iterdir():
        vendor_file: Path = device / "vendor"

        if not vendor_file.exists():
            continue

        vendors.add(vendor_file.read_text().strip().lower())

    return vendors


def get_usb_vendors() -> set[str]:
    if not USB_DEVICES.is_dir():
        return set()

    vendors: set[str] = set()

    for device in USB_DEVICES.iterdir():
        vendor_file: Path = device / "idVendor"

        if not vendor_file.exists():
            continue

        vendors.add(vendor_file.read_text().strip().lower())

    return vendors


def get_loaded_modules() -> set[str]:
    try:
        lines: list[str] = MODULES.read_text().splitlines()
    except FileNotFoundError:
        return set()

    return {line.split()[0] for line in lines if line.strip()}


def get_firmware_packages() -> set[str]:
    """
    The `linux-firmware-*` packages this machine needs.

    Replaces the `linux-firmware` meta package, which depends on every vendor
    split and installs roughly 400 MiB regardless of the hardware present.

    Detection only sees devices attached when decman runs. A wifi dongle plugged
    in later is not covered, so a rebuild is needed after adding hardware that
    needs its own firmware.
    """
    pci_vendors: set[str] = get_pci_vendors()
    usb_vendors: set[str] = get_usb_vendors()
    modules: set[str] = get_loaded_modules()

    if not pci_vendors and not usb_vendors:
        # sysfs is unavailable or unreadable. Fall back to the meta package
        # rather than risk omitting firmware a device needs to come up.
        return {"linux-firmware"}

    packages: set[str] = set(ALWAYS_INSTALLED_FIRMWARE)

    if utils.hardware.cpu_vendor.is_cpu_amd():
        # Non-GPU AMD device firmware (PSP, XHCI, sensor fusion hub)
        packages.add("linux-firmware-amd")

    for vendor in pci_vendors:
        if vendor in PCI_VENDOR_FIRMWARE:
            packages.add(PCI_VENDOR_FIRMWARE[vendor])

    for vendor in usb_vendors:
        if vendor in USB_VENDOR_FIRMWARE:
            packages.add(USB_VENDOR_FIRMWARE[vendor])

    for module in modules:
        if module in MODULE_FIRMWARE:
            packages.add(MODULE_FIRMWARE[module])

    return packages
