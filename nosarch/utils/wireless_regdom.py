import re
from pathlib import Path


def get_wireless_regdom_contents() -> str | None:
    """Return the wireless-regdom file contents, or None if undeterminable."""

    timezone: str | None = _get_timezone()
    if timezone is None:
        return None

    country: str | None = timezone.split("/", 1)[0]

    if not re.fullmatch(r"[A-Z]{2}", country):
        country = _country_from_zone_tab(timezone)

    if country is None or not re.fullmatch(r"[A-Z]{2}", country):
        return None

    return f'WIRELESS_REGDOM="{country}"\n'


def _get_timezone() -> str | None:
    try:
        target: Path = Path("/etc/localtime").resolve()
        # `/etc/localtime` is a symlink to the appropriate timezone file in `/usr/share/zoneinfo`

        return str(target.relative_to(Path("/usr/share/zoneinfo")))
        # Remove the `/usr/share/zoneinfo` prefix from the path to get the timezone
    except OSError:
        return None
    except ValueError:
        return None


def _country_from_zone_tab(timezone: str) -> str | None:
    try:
        with Path("/usr/share/zoneinfo/zone.tab").open() as f:
            for line in f:
                line: str = line.strip()

                if not line or line.startswith("#"):
                    continue

                country, _, tz, *_ = line.split("\t")
                if tz == timezone:
                    return country
    except OSError:
        return None


if __name__ == "__main__":
    print(get_wireless_regdom_contents())
