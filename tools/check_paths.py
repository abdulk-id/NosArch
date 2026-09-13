"""
Checks that NosArch-owned paths referenced in dotfiles/ (unit files, udev
rules, shell scripts) actually resolve against what the modules deploy.

Catches the class of bug where a script moves or is deleted but a reference
to its old path survives elsewhere in the repo: decman has no way to notice
this on its own

Usage: python3 tools/check_paths.py
Exit status is nonzero if any dangling reference is found.
"""

import re
import sys
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DOTFILES_ROOT: Path = REPO_ROOT / "dotfiles"

# dotfiles/<this>/ is a convention marker, not a deployed root.
UNDEPLOYED_DIRS: set[str] = {"unused-config"}

# Only paths under these prefixes are NosArch's responsibility to get right.
# Anything else under /usr, /etc etc. is provided by a package and this
# script has no way to verify it.
#
# This is deliberately the whole of `/usr/local/bin`, not just the
# `nosarch/` and `util/` subdirectories NosArch currently deploys into. A
# narrower prefix is matched against the *referenced* string, so a typo that
# corrupts the subdirectory itself (`nosarch-lock-helper.sh` under
# `/usr/local/bin/uti/` instead of `/usr/local/bin/util/`) makes the broken
# reference stop matching the prefix and silently drops out of scope — the
# opposite of what this script is for. Nothing under `/usr/local/bin` is
# package-managed by convention (see FHS 3.0 §4.7), so widening to the whole
# directory does not risk false positives against package-owned paths.
OWNED_PATH_PREFIXES: tuple[str, ...] = ("/usr/local/bin", "/usr/lib/nosarch")

PATH_PATTERN: re.Pattern[str] = re.compile(r'(?<![\w"])(/(?:usr|etc|opt)/[A-Za-z0-9._/-]+)')


def deployed_paths() -> set[str]:
    """
    Every path `dotfiles/<root>/<rest>` would deploy to, across all module
    roots, as `/<rest>` with the per-user home placeholder normalized.
    """
    paths: set[str] = set()

    for module_root in DOTFILES_ROOT.iterdir():
        if not module_root.is_dir() or module_root.name in UNDEPLOYED_DIRS:
            continue

        for entry in module_root.rglob("*"):
            if not entry.is_file():
                continue

            relative: Path = entry.relative_to(module_root)
            deployed: str = "/" + str(relative).replace("home/username", "home/USER")
            paths.add(deployed)

    return paths


def referenced_paths(deployed: set[str]) -> list[tuple[Path, int, str]]:
    """
    (file, line number, path) for every NosArch-owned path referenced
    somewhere in dotfiles/ that does not resolve as deployed or as a path
    that already exists on the machine running this check.
    """
    findings: list[tuple[Path, int, str]] = []

    for source_file in DOTFILES_ROOT.rglob("*"):
        if not source_file.is_file() or "unused-config" in source_file.parts:
            continue

        try:
            text: str = source_file.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("#"):
                continue

            for match in PATH_PATTERN.finditer(line):
                path: str = match.group(1)

                if not path.startswith(OWNED_PATH_PREFIXES):
                    continue

                if path in deployed or Path(path).exists():
                    continue

                findings.append((source_file.relative_to(REPO_ROOT), line_number, path))

    return findings


def main() -> int:
    deployed: set[str] = deployed_paths()
    findings: list[tuple[Path, int, str]] = referenced_paths(deployed)

    if not findings:
        print("[CHECKS] SUCCESS: No dangling NosArch-owned path references.")
        return 0

    print("[CHECKS] ERROR: Dangling NosArch-owned path references:")

    for source_file, line_number, path in sorted(findings):
        print(f"  {source_file}:{line_number}  ->  {path}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
