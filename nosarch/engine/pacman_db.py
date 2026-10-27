"""Reads pacman's local database through pacman itself, which needs no root."""

import re
from dataclasses import dataclass, field

import engine.command

_FIELD: re.Pattern[str] = re.compile(r"^(\S[^:]*?)\s*: (.*)$")

# pacman localizes its field names. The C locale keeps them parseable.
_ENV: dict[str, str] = {"LC_ALL": "C"}


@dataclass
class LocalPackage:
    name: str
    version: str
    explicit: bool
    native: bool
    required_by: set[str] = field(default_factory=set)


def _query(*args: str) -> str:
    return engine.command.run(["pacman", *args], env=_ENV, capture=True, check=False)


def local_packages() -> dict[str, LocalPackage]:
    """Every installed package. Native means it exists in a configured sync repository."""

    native: set[str] = set(_query("-Qqn").split())
    packages: dict[str, LocalPackage] = {}

    for block in _query("-Qi").split("\n\n"):
        fields: dict[str, str] = {}
        last: str | None = None

        for line in block.splitlines():
            match: re.Match[str] | None = _FIELD.match(line)
            if match:
                last = match.group(1)
                fields[last] = match.group(2).strip()
            elif last is not None and line.startswith(" "):
                # A long field wraps onto indented continuation lines.
                fields[last] += " " + line.strip()

        name: str | None = fields.get("Name")
        if name is None:
            continue

        required_by: str = fields.get("Required By", "None")
        packages[name] = LocalPackage(
            name=name,
            version=fields.get("Version", ""),
            explicit=fields.get("Install Reason", "").startswith("Explicitly"),
            native=name in native,
            required_by=set() if required_by == "None" else set(required_by.split()),
        )

    return packages


def orphans(packages: dict[str, LocalPackage], native: bool) -> set[str]:
    """
    Packages installed as dependencies that nothing outside the returned set needs, native or foreign.

    Pruned until stable, so a dependency only needed by another orphan is an orphan too.
    """

    candidates: set[str] = {name for name, pkg in packages.items() if not pkg.explicit and pkg.native == native}

    changed: bool = True
    while changed:
        changed = False
        for name in tuple(candidates):
            if packages[name].required_by - candidates:
                candidates.remove(name)
                changed = True

    return candidates


def dependants(packages: dict[str, LocalPackage], name: str) -> set[str]:
    """`name` and every installed package that needs it, directly or not."""

    seen: set[str] = set()
    stack: list[str] = [name]

    while stack:
        current: str = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in packages:
            stack.extend(packages[current].required_by - seen)

    return seen


def split_removals(
    packages: dict[str, LocalPackage], candidates: set[str], keep: set[str]
) -> tuple[set[str], set[str]]:
    """
    Splits packages nothing declares into the ones to remove and the ones to keep as dependencies.

    A package something kept still needs is marked as a dependency instead of removed, so it goes once nothing
    needs it.
    """

    remove: set[str] = set()
    demote: set[str] = set()

    for name in candidates:
        if dependants(packages, name) & keep:
            demote.add(name)
        else:
            remove.add(name)

    return remove, demote
