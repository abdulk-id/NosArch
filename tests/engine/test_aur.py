"""The foreign package step: the installer package stays, and pacman does not prompt."""

from __future__ import annotations

import harness
import pytest

import nosarch.engine.aur
import nosarch.engine.pacman_db

STEPS: tuple[str, ...] = ("aur",)


def _installed(*packages: nosarch.engine.pacman_db.LocalPackage) -> dict[str, nosarch.engine.pacman_db.LocalPackage]:
    return {package.name: package for package in packages}


def _package(
    name: str, *, explicit: bool = True, required_by: set[str] | None = None
) -> nosarch.engine.pacman_db.LocalPackage:
    return nosarch.engine.pacman_db.LocalPackage(
        name, "1.0.0-1", explicit=explicit, native=False, required_by=required_by or set()
    )


def _block_aur(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(self: nosarch.engine.aur.Rpc, url: str) -> dict:
        raise AssertionError(url)

    monkeypatch.setattr(nosarch.engine.aur.Rpc, "_request", fail)


def test_the_installer_package_is_kept_and_another_foreign_package_is_removed(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_aur(monkeypatch)
    monkeypatch.setattr(
        nosarch.engine.pacman_db, "local_packages", lambda: _installed(_package("nosarch"), _package("spotify"))
    )

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [["pacman", "-Rs", "--noconfirm", "spotify"]]


def test_a_dependency_of_the_installer_package_is_demoted_instead_of_removed(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The dependency stays installed, so the step asks the AUR whether to upgrade it. Nothing is published there.
    monkeypatch.setattr(nosarch.engine.aur.Rpc, "_request", lambda self, url: {"results": []})
    monkeypatch.setattr(
        nosarch.engine.pacman_db,
        "local_packages",
        lambda: _installed(_package("nosarch"), _package("helper", required_by={"nosarch"})),
    )

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [["pacman", "-D", "--asdeps", "helper"]]


def test_the_installer_package_is_kept_when_it_was_installed_as_a_dependency(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_aur(monkeypatch)
    monkeypatch.setattr(
        nosarch.engine.pacman_db, "local_packages", lambda: _installed(_package("nosarch", explicit=False))
    )

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == []
