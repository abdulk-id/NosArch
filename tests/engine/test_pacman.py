"""The pacman step: database sync, and pacman transactions that must not prompt."""

from __future__ import annotations

from pathlib import Path

import harness
import pytest

import nosarch.engine.pacman_db
from nosarch.engine.steps import pacman

STEPS: tuple[str, ...] = ("pacman",)
_missing_sync_databases = pacman.missing_sync_databases


@pytest.fixture(autouse=True)
def databases_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The host's pacman databases must not change what a test records."""
    monkeypatch.setattr(pacman, "missing_sync_databases", lambda conf_path="/etc/pacman.conf": [])


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


def test_a_missing_database_is_downloaded_before_pacman_is_queried(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pacman warns about a missing database on every command except a sync. The queries have to come after -Sy.
    monkeypatch.setattr(pacman, "missing_sync_databases", lambda conf_path="/etc/pacman.conf": ["multilib"])

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [
        ["pacman", "-Sy", "--noconfirm"],
        ["pacman", "-Qqn"],
        ["pacman", "-Qi"],
        ["pacman", "-Syu", "--noconfirm"],
    ]


def test_a_dry_run_does_not_download_a_missing_database(box: harness.Box, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pacman, "missing_sync_databases", lambda conf_path="/etc/pacman.conf": ["multilib"])

    box.apply(box.rec("m"), steps=STEPS, dry_run=True)

    assert box.argv == [["pacman", "-Qqn"], ["pacman", "-Qi"]]


def test_an_enabled_repository_without_a_database_file_is_missing(tmp_path: Path) -> None:
    database: Path = tmp_path / "db"
    (database / "sync").mkdir(parents=True)
    (database / "sync" / "core.db").write_text("", encoding="utf-8")
    conf: Path = tmp_path / "pacman.conf"
    conf.write_text(
        "\n".join(
            [
                "[options]",
                f"DBPath = {database}",
                "HoldPkg = pacman glibc",
                "",
                "[core]",
                "Include = /etc/pacman.d/mirrorlist",
                "",
                "#[multilib-testing]",
                "#Include = /etc/pacman.d/mirrorlist",
                "",
                "[multilib]",
                "Include = /etc/pacman.d/mirrorlist",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert _missing_sync_databases(str(conf)) == ["multilib"]


def test_a_missing_pacman_configuration_is_left_alone(tmp_path: Path) -> None:
    assert _missing_sync_databases(str(tmp_path / "missing.conf")) == []
