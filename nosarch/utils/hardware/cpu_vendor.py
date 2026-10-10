from functools import lru_cache


def _get_cpu_info_line(line_prefix: str) -> str | None:
    with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(line_prefix):
                # Lines in cpuinfo are always written as `key : values`. Only return values
                return line.split(":", 1)[1].strip()

    return None


# CPU Vendor
@lru_cache(maxsize=1)
def get_cpu_vendor() -> str:
    cpu_vendor: str | None = _get_cpu_info_line("vendor_id")
    if cpu_vendor is None:
        raise RuntimeError("Could not determine CPU vendor")

    return cpu_vendor


def is_cpu_intel() -> bool:
    return get_cpu_vendor() == "GenuineIntel"


def is_cpu_amd() -> bool:
    return get_cpu_vendor() == "AuthenticAMD"


# CPU Specifics
@lru_cache(maxsize=1)
def is_intel_hybrid() -> bool:
    """True on Intel hybrid (P-core/E-core) parts."""

    if not is_cpu_intel():
        return False

    cpu_hybrid: str | None = _get_cpu_info_line("flags")
    if cpu_hybrid is None:
        return False

    return "hybrid" in cpu_hybrid
