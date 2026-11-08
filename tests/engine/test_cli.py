"""`engine.app.main`: the arguments it takes, when it asks for root, and the exit codes errors turn into."""

from __future__ import annotations

import sys
from collections.abc import Callable

import engine
import engine.app
import engine.command
import engine.fs
import harness
import pytest


class _Reexec(Exception):
    """Stands in for `os.execvp("sudo", ...)`, which never returns."""


@pytest.fixture
def as_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def reexec() -> None:
        raise _Reexec

    monkeypatch.setattr(engine.command, "is_root", lambda: False)
    monkeypatch.setattr(engine.app, "_reexec_as_root", reexec)


def _main(monkeypatch: pytest.MonkeyPatch, setup: Callable[[], engine.Setup], *arguments: str) -> None:
    monkeypatch.setattr(sys, "argv", ["apply.py", *arguments])
    engine.app.main(setup)


def test_a_dry_run_needs_no_root(box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None) -> None:
    _main(monkeypatch, lambda: engine.Setup(steps=["files"]), "--dry-run")

    assert box.state() is None


def test_a_real_run_asks_for_root_first(box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None) -> None:
    built: list[bool] = []

    with pytest.raises(_Reexec):
        _main(monkeypatch, lambda: built.append(True) or engine.Setup(steps=["files"]))

    assert built == []


def test_a_command_that_fails_exits_1_and_shows_its_output(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)
    box.commands.fail("systemctl", "enable")

    with pytest.raises(SystemExit) as exit_:
        _main(monkeypatch, lambda: _setup(box, units={"a.service"}), "--only", "systemd")

    assert exit_.value.code == 1
    assert "Command 'systemctl enable a.service' returned with a non-zero exit code 1" in capsys.readouterr().err


def _setup(box: harness.Box, **declarations: object) -> engine.Setup:
    setup: engine.Setup = engine.Setup(steps=["files", "systemd"])
    setup.add(box.rec("m", **declarations))
    return setup


def test_a_file_that_cannot_be_installed_exits_1(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)
    files: dict[str, engine.File] = {box.path("a"): engine.File(source_file=box.path("missing"))}

    with pytest.raises(SystemExit) as exit_:
        _main(monkeypatch, lambda: _setup(box, files=files), "--only", "files")

    assert exit_.value.code == 1
    assert "Source file doesn't exist" in capsys.readouterr().err


def test_an_unknown_step_exits_1(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)

    with pytest.raises(SystemExit) as exit_:
        _main(monkeypatch, lambda: _setup(box), "--skip", "nosuchstep")

    assert exit_.value.code == 1
    assert "Unknown step 'nosuchstep'" in capsys.readouterr().err


def test_a_definition_that_raises_a_value_error_exits_1(
    box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)

    def broken() -> engine.Setup:
        engine.File()
        return engine.Setup()

    with pytest.raises(SystemExit) as exit_:
        _main(monkeypatch, broken)

    assert exit_.value.code == 1
    assert "ValueError raised from the source" in capsys.readouterr().err


def _interrupt() -> None:
    raise KeyboardInterrupt


def test_ctrl_c_exits_130(box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)

    with pytest.raises(SystemExit) as exit_:
        _main(monkeypatch, lambda: _setup(box, actions={"before_update": _interrupt}))

    assert exit_.value.code == 130


def test_no_hooks_runs_no_hook(box: harness.Box, monkeypatch: pytest.MonkeyPatch, as_user: None) -> None:
    monkeypatch.setattr(engine.command, "is_root", lambda: True)

    _main(monkeypatch, lambda: _setup(box), "--no-hooks")

    assert box.hooks == []
