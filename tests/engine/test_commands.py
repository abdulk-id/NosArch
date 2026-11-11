"""The command runner, `nosarch.engine.command.run`, against real processes. Nothing else in the suite runs a command."""

from __future__ import annotations

import getpass
import os
import pwd
from pathlib import Path

import harness
import pytest

import nosarch.engine.command
from nosarch.engine.command import CommandFailedError, sh, succeeds


def test_capture_returns_stdout_only(capfd: pytest.CaptureFixture[str]) -> None:
    # Output that definition code parses, such as `loginctl`, must not get the error text mixed in.
    output: str = harness.real_run(["sh", "-c", "echo out; echo err >&2"], capture=True)

    assert output == "out\n"
    assert capfd.readouterr().err == "err\n"


def test_without_capture_nothing_is_returned_and_the_command_streams(capfd: pytest.CaptureFixture[str]) -> None:
    assert harness.real_run(["echo", "shown"]) == ""
    assert capfd.readouterr().out == "shown\n"


def test_a_failing_command_raises_with_its_code_and_output() -> None:
    with pytest.raises(CommandFailedError, match="non-zero exit code 3") as error:
        harness.real_run(["sh", "-c", "echo oops; exit 3"], capture=True)

    assert error.value.code == 3
    assert error.value.output == "oops\n"
    assert error.value.cmd == ["sh", "-c", "echo oops; exit 3"]


def test_an_unchecked_failure_warns_and_returns_the_output(capsys: pytest.CaptureFixture[str]) -> None:
    output: str = harness.real_run(["sh", "-c", "echo oops; exit 3"], capture=True, check=False)

    assert output == "oops\n"
    assert "returned with an exit code 3" in capsys.readouterr().err


def test_a_missing_program_raises_code_127_or_warns(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(CommandFailedError) as error:
        harness.real_run(["nosuchtool", "x"])
    assert error.value.code == 127

    assert harness.real_run(["nosuchtool", "x"], check=False) == ""
    assert "Could not run 'nosuchtool x'" in capsys.readouterr().err


def test_output_that_is_not_utf8_is_decoded_with_replacement_characters() -> None:
    assert harness.real_run(["printf", "a\\377b"], capture=True) == "a\ufffdb"


def test_env_is_merged_over_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARITY_KEPT", "kept")

    output: str = harness.real_run(["sh", "-c", 'echo "$PARITY_A|$PARITY_KEPT"'], env={"PARITY_A": "1"}, capture=True)

    assert output == "1|kept\n"


def test_without_pass_environment_only_the_overrides_remain() -> None:
    output: str = harness.real_run(["env"], env={"PARITY_A": "1"}, pass_environment=False, capture=True)

    assert output == "PARITY_A=1\n"


def test_cwd_is_where_the_command_starts(tmp_path: Path) -> None:
    assert harness.real_run(["pwd"], cwd=str(tmp_path), capture=True) == f"{tmp_path}\n"


def test_a_command_run_as_a_user_gets_that_users_login_environment() -> None:
    # A command run as a user, such as brew or mise, needs that user's HOME.
    me: pwd.struct_passwd = pwd.getpwuid(os.geteuid())

    output: str = harness.real_run(["sh", "-c", 'echo "$HOME|$USER|$LOGNAME|$SHELL"'], user=me.pw_name, capture=True)

    assert output == f"{me.pw_dir}|{me.pw_name}|{me.pw_name}|{me.pw_shell}\n"


def test_a_user_that_does_not_exist_is_reported_by_name() -> None:
    with pytest.raises(nosarch.engine.command.AccountNotFoundError, match="The user 'nosuchuser' doesn't exist"):
        harness.real_run(["true"], user="nosuchuser")


@pytest.mark.skipif(os.geteuid() == 0, reason="root can run as anyone")
def test_running_as_someone_else_needs_root() -> None:
    with pytest.raises(PermissionError, match="needs root"):
        harness.real_run(["true"], user="root")


def test_can_run_as_is_true_for_yourself() -> None:
    assert nosarch.engine.command.can_run_as(getpass.getuser())


def test_sh_runs_its_string_through_bin_sh(tmp_path: Path) -> None:
    sh(f"echo $0 a b > {tmp_path}/out")

    assert (tmp_path / "out").read_text() == "/bin/sh a b\n"


def test_succeeds_is_the_exit_status() -> None:
    assert succeeds(["true"])
    assert not succeeds(["false"])
    assert not succeeds(["nosuchtool"])
