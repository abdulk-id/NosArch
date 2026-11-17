"""The pacman step runs install, upgrade, and removal without asking."""

from __future__ import annotations

import harness
import pytest

import nosarch.engine.pacman_db
from nosarch.engine.steps import pacman

STEPS: tuple[str, ...] = ("pacman",)


class _Declared(harness.Rec):
    def __init__(self, log: list[str], names: set[str]) -> None:
        super().__init__("m", log)
        self._names: set[str] = names

    @pacman.packages
    def pkgs(self) -> set[str]:
        return set(self._names)


def test_transactions_do_not_prompt(box: harness.Box) -> None:
    box.apply(_Declared(box.log, {"git"}), steps=STEPS)

    assert box.argv == [
        ["pacman", "-Qqn"],
        ["pacman", "-Qi"],
        ["pacman", "-Syu", "--noconfirm"],
        ["pacman", "-S", "--needed", "--noconfirm", "git"],
        ["pacman", "-D", "--asexplicit", "git"],
    ]


def test_a_dry_run_only_queries(box: harness.Box) -> None:
    box.apply(_Declared(box.log, {"git"}), steps=STEPS, dry_run=True)

    assert box.argv == [["pacman", "-Qqn"], ["pacman", "-Qi"]]


def test_removing_an_undeclared_package_does_not_prompt(box: harness.Box, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nosarch.engine.pacman_db,
        "local_packages",
        lambda: {"leftover": nosarch.engine.pacman_db.LocalPackage("leftover", "1-1", explicit=True, native=True)},
    )

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [["pacman", "-Rs", "--noconfirm", "leftover"], ["pacman", "-Syu", "--noconfirm"]]
