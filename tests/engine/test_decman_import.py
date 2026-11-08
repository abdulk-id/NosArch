"""Switching from decman: its store becomes the engine's state, so the first run does not treat everything as new."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import engine
import engine.app
import engine.command
import engine.state
import harness
import pytest


def _set(*items: str) -> dict[str, Any]:
    return {"__type__": "set", "items": list(items)}


def _write_store(box: harness.Box, store: dict[str, Any]) -> None:
    Path(engine.state.DECMAN_STORE).parent.mkdir(parents=True, exist_ok=True)
    Path(engine.state.DECMAN_STORE).write_text(json.dumps(store))


def test_the_store_becomes_the_state(box: harness.Box, accounts: harness.Accounts) -> None:
    accounts.add_user("alice", 1000, 1000)
    accounts.add_user("aurbuilduser", 970, 970)
    _write_store(
        box,
        {
            "enabled_modules": ["usermanager", "m"],
            "all_files": ["/etc/a", "/etc/b"],
            "packages_for_module": {"m": _set("git"), "usermanager": _set()},
            "custom_packages_for_module": {"m": _set("CustomPackage(pkgname=foo, pkgbuild_directory=/x)")},
            "systemd_units_for_module": {"m": _set("a.service")},
            "systemd_user_units_for_module": {"m": {"alice": _set("x.service")}},
            "snaps_for_module": {"m": {"code": "latest/stable"}},
            "systemd_units": _set("a.service"),
            "systemd_user_units": {"alice": _set("x.service")},
            "usermanager_users": _set("alice", "aurbuilduser", "gone"),
            "pkgbuild_latest_reviewed_commits": {"base": "abc"},
        },
    )

    state: engine.state.State = engine.state.import_decman_store()

    assert state.enabled_modules == ["m"]
    assert state.files == {engine.state.IMPORTED_FILES_OWNER: ["/etc/a", "/etc/b"]}
    assert state.declared == {
        "m": {
            "pacman": ["git"],
            "custom": ["foo"],
            "systemd": ["a.service"],
            "systemd_user": ["alice:x.service"],
            "snap": ["code"],
        }
    }
    assert state.systemd_units == ["a.service"]
    assert state.systemd_user_units == {"alice": ["x.service"]}
    # Only a system account is taken as created by decman, so a login user is never deleted.
    assert state.created_users == ["aurbuilduser"]
    assert state.aur_reviewed == {"base": "abc"}


def test_the_first_run_imports_instead_of_enabling_everything(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, accounts: harness.Accounts
) -> None:
    kept: str = box.write("etc/kept", "kept\n")
    old: str = box.write("etc/old", "old\n")
    _write_store(box, {"enabled_modules": ["m"], "all_files": [kept, old]})
    monkeypatch.setattr(engine.command, "is_root", lambda: True)

    module: harness.Rec = box.rec("m", files={kept: engine.File(content="kept\n")})
    box.apply(module)

    # No on_enable, since decman enabled it. The file nothing declares any more goes, and no module hears of it.
    assert box.hooks == ["before_update:m", "after_update:m"]
    assert not box.exists("etc/old")
    assert box.state().files == {"m": [kept]}  # pyright: ignore[reportOptionalMemberAccess]


def test_a_dry_run_without_root_cannot_read_the_store_and_says_so(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_store(box, {"enabled_modules": ["m"]})
    monkeypatch.setattr(engine.command, "is_root", lambda: False)

    box.apply(box.rec("m"), dry_run=True)

    assert "Run `nosarch/apply.py --import-decman`" in capsys.readouterr().err


def test_import_decman_saves_the_state_and_stops(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, accounts: harness.Accounts
) -> None:
    _write_store(box, {"enabled_modules": ["m"]})
    monkeypatch.setattr(engine.command, "is_root", lambda: True)
    monkeypatch.setattr(sys, "argv", ["apply.py", "--import-decman"])

    engine.app.main(lambda: pytest.fail("the setup is not needed to import"))

    assert box.state().enabled_modules == ["m"]  # pyright: ignore[reportOptionalMemberAccess]
