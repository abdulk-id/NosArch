from pathlib import Path


def get_cpu_vendor() -> str:
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("vendor_id"):
            return line.split(":")[1].strip()

    raise RuntimeError("Could not determine CPU vendor")


def is_cpu_intel() -> bool:
    return get_cpu_vendor() == "GenuineIntel"


def is_cpu_amd() -> bool:
    return get_cpu_vendor() == "AuthenticAMD"
