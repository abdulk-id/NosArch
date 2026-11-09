"""The order of a run, what ends one early, and what the engine remembers afterwards."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from pathlib import Path

import engine
import engine.fs
import engine.state
import harness
import pytest


def _raise(message: str) -> Callable[[], None]:
    def raiser() -> None:
        raise RuntimeError(message)

    return raiser


def _a_file(box: harness.Box, name: str) -> dict[str, engine.File]:
    return {box.path(name): engine.File(content=f"{name}\n")}


# --- Order ------------------------------------------------------------------------------------------------------------
def test_phases_run_in_order_and_each_walks_modules_in_registration_order(box: harness.Box) -> None:
    box.apply(
        box.rec("c", files=_a_file(box, "c"), units={"c.service"}),
        box.rec("a", files=_a_file(box, "a")),
        box.rec("b", files=_a_file(box, "b")),
        steps=("files", "systemd"),
    )

    assert box.hooks == [
        *(f"before_update:{name}" for name in "cab"),
        *(f"on_enable:{name}" for name in "cab"),
        *(f"on_change:{name}" for name in "cab"),
        *(f"after_update:{name}" for name in "cab"),
    ]
    assert box.state().enabled_modules == ["c", "a", "b"]  # pyright: ignore[reportOptionalMemberAccess]


def test_steps_run_after_before_update_and_before_on_enable(box: harness.Box) -> None:
    box.apply(box.rec("a", units={"a.service"}), steps=("systemd",))

    assert box.log == [
        "before_update:a",
        "cmd systemctl enable a.service",
        "cmd systemctl daemon-reload",
        "on_enable:a",
        "on_change:a",
        "after_update:a",
    ]


def test_a_second_identical_run_fires_neither_on_enable_nor_on_change(box: harness.Box) -> None:
    def module() -> harness.Rec:
        return box.rec("a", files=_a_file(box, "a"), units={"a.service"})

    box.apply(module(), steps=("files", "systemd"))
    box.apply(module(), steps=("files", "systemd"))

    assert box.hooks == ["before_update:a", "after_update:a"]
    assert box.argv == [["systemctl", "daemon-reload"]]


def test_a_new_module_with_nothing_declared_gets_on_enable_and_never_on_change(box: harness.Box) -> None:
    box.apply(box.rec("empty"))
    assert box.hooks == ["before_update:empty", "on_enable:empty", "after_update:empty"]

    box.apply(box.rec("empty"))
    assert box.hooks == ["before_update:empty", "after_update:empty"]


# --- Choosing steps ---------------------------------------------------------------------------------------------------
def test_only_runs_the_named_steps_in_the_configured_order(box: harness.Box) -> None:
    box.apply(
        box.rec("m", files=_a_file(box, "a"), units={"a.service"}),
        steps=("files", "systemd"),
        only=["systemd", "files"],
    )

    assert box.exists("a")
    assert box.argv[0] == ["systemctl", "enable", "a.service"]


def test_skip_leaves_a_step_out(box: harness.Box) -> None:
    box.apply(box.rec("m", files=_a_file(box, "a"), units={"a.service"}), steps=("files", "systemd"), skip=["systemd"])

    assert box.exists("a")
    assert box.argv == []


def test_a_run_limited_to_files_does_not_record_unit_declarations(box: harness.Box) -> None:
    def module() -> harness.Rec:
        return box.rec("m", units={"a.service"})

    box.apply(module(), steps=("files", "systemd"), only=["files"])
    assert box.argv == []

    box.apply(module(), steps=("files", "systemd"))

    assert box.hooks == ["before_update:m", "on_change:m", "after_update:m"]
    assert box.argv == [["systemctl", "enable", "a.service"], ["systemctl", "daemon-reload"]]


@pytest.mark.parametrize("flag", ["only", "skip"])
def test_a_step_that_does_not_exist_fails_before_anything_runs(box: harness.Box, flag: str) -> None:
    # A mistyped step name must not silently run nothing.
    with pytest.raises(ValueError, match="Unknown step 'nosuchstep'"):
        box.apply(box.rec("m", files=_a_file(box, "a")), **{flag: ["nosuchstep"]})

    assert box.hooks == []
    assert not box.exists("a")


def test_a_step_that_does_not_exist_in_the_setup_fails_too(box: harness.Box) -> None:
    with pytest.raises(ValueError, match="Unknown step 'nosuchplugin'"):
        box.apply(box.rec("m", files=_a_file(box, "a")), steps=("files", "nosuchplugin"))


def test_no_hooks_deploys_and_the_next_run_catches_up(box: harness.Box) -> None:
    def modules() -> tuple[harness.Rec, harness.Rec]:
        return box.rec("a", files=_a_file(box, "a")), box.rec("b", files=_a_file(box, "b"))

    box.apply(*modules(), no_hooks=True)

    assert box.hooks == []
    assert box.read("a") == "a\n"
    assert box.state().enabled_modules == []  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(*modules())

    # The files are already in place, so only the change the first run saved can tell on_change about them.
    assert box.hooks == [
        "before_update:a",
        "before_update:b",
        "on_enable:a",
        "on_enable:b",
        "on_change:a",
        "on_change:b",
        "after_update:a",
        "after_update:b",
    ]


# --- Dry runs ---------------------------------------------------------------------------------------------------------
def test_a_dry_run_runs_nothing_but_still_asks_for_declarations(
    box: harness.Box, capsys: pytest.CaptureFixture[str]
) -> None:
    box.apply(box.rec("m", files=_a_file(box, "a"), units={"a.service"}), steps=("files", "systemd"))
    saved: str = Path(engine.state.STATE_FILE).read_text()
    asked: list[str] = []

    class Counting(harness.Rec):
        def files(self) -> dict[str, engine.File]:
            asked.append("files")
            return {box.path("a"): engine.File(content="changed\n")}

    box.apply(
        Counting("m", box.log, units={"a.service", "b.service"}),
        box.rec("new", files=_a_file(box, "n")),
        steps=("files", "systemd"),
        dry_run=True,
    )

    assert box.hooks == []
    assert box.argv == []
    assert box.read("a") == "a\n"
    assert not box.exists("n")
    assert asked == ["files"]
    assert Path(engine.state.STATE_FILE).read_text() == saved
    printed: str = capsys.readouterr().out
    assert "Enabling systemd units:" in printed
    assert "b.service" in printed


# --- Failures ---------------------------------------------------------------------------------------------------------
def test_a_failing_step_skips_every_later_step_and_hook(box: harness.Box) -> None:
    missing: dict[str, engine.File] = {box.path("a"): engine.File(source_file=box.path("missing"))}

    with pytest.raises(engine.fs.InstallError):
        box.apply(box.rec("a", files=missing, units={"a.service"}), steps=("files", "systemd"))

    assert box.hooks == ["before_update:a"]
    assert box.argv == []
    assert box.state() is None or box.state().enabled_modules == []  # pyright: ignore[reportOptionalMemberAccess]


def test_a_raising_before_update_stops_the_run_before_any_step(box: harness.Box) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        box.apply(
            box.rec("a", files=_a_file(box, "a")),
            box.rec("b", actions={"before_update": _raise("boom")}),
            steps=("files",),
        )

    assert box.hooks == ["before_update:a", "before_update:b"]
    assert not box.exists("a")
    assert box.state() is None


def test_a_raising_on_enable_records_only_the_modules_before_it(box: harness.Box) -> None:
    with pytest.raises(RuntimeError):
        box.apply(box.rec("a"), box.rec("b", actions={"on_enable": _raise("boom")}), box.rec("c"))

    assert box.hooks == ["before_update:a", "before_update:b", "before_update:c", "on_enable:a", "on_enable:b"]
    assert box.state().enabled_modules == ["a"]  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(box.rec("a"), box.rec("b"), box.rec("c"))

    assert box.hooks == [
        *(f"before_update:{name}" for name in "abc"),
        "on_enable:b",
        "on_enable:c",
        *(f"after_update:{name}" for name in "abc"),
    ]
    assert box.state().enabled_modules == ["a", "b", "c"]  # pyright: ignore[reportOptionalMemberAccess]


def test_a_raising_on_change_ends_the_run_and_the_state_is_saved(box: harness.Box) -> None:
    with pytest.raises(RuntimeError):
        box.apply(
            box.rec("a", files=_a_file(box, "a"), actions={"on_change": _raise("boom")}),
            box.rec("b", files=_a_file(box, "b")),
        )

    assert box.hooks == ["before_update:a", "before_update:b", "on_enable:a", "on_enable:b", "on_change:a"]
    assert box.state().enabled_modules == ["a", "b"]  # pyright: ignore[reportOptionalMemberAccess]
    # Nothing declared changed on the next run, but neither module has heard of its files yet.
    box.apply(box.rec("a", files=_a_file(box, "a")), box.rec("b", files=_a_file(box, "b")))
    assert box.hooks == [
        "before_update:a",
        "before_update:b",
        "on_change:a",
        "on_change:b",
        "after_update:a",
        "after_update:b",
    ]


def test_a_raising_after_update_skips_the_later_after_updates(box: harness.Box) -> None:
    with pytest.raises(RuntimeError):
        box.apply(box.rec("a", actions={"after_update": _raise("boom")}), box.rec("b"))

    assert box.hooks == ["before_update:a", "before_update:b", "on_enable:a", "on_enable:b", "after_update:a"]
    assert box.state().enabled_modules == ["a", "b"]  # pyright: ignore[reportOptionalMemberAccess]


# --- State ------------------------------------------------------------------------------------------------------------
def test_state_is_saved_after_success_and_after_failure_and_not_after_a_dry_run(box: harness.Box) -> None:
    a: str = box.path("a")
    box.apply(box.rec("m", files={a: engine.File(content="a\n")}))
    saved: str = Path(engine.state.STATE_FILE).read_text()

    with pytest.raises(engine.fs.InstallError):
        box.apply(box.rec("m", files={a: engine.File(source_file=box.path("missing"))}))
    after_failure: str = Path(engine.state.STATE_FILE).read_text()
    box.apply(box.rec("m", files={a: engine.File(content="a\n")}), dry_run=True)

    assert json.loads(saved)["enabled_modules"] == ["m"]
    assert json.loads(saved)["files"] == {"m": [a]}
    assert json.loads(after_failure)["files"] == {"m": [a]}
    assert Path(engine.state.STATE_FILE).read_text() == after_failure


def test_state_is_readable_by_everyone(box: harness.Box) -> None:
    box.apply(box.rec("a", files=_a_file(box, "a")))

    assert stat.S_IMODE(os.stat(engine.state.STATE_FILE).st_mode) == 0o644


def test_a_corrupt_state_file_stops_the_run_before_anything_changes(box: harness.Box) -> None:
    Path(engine.state.STATE_FILE).parent.mkdir(parents=True)
    Path(engine.state.STATE_FILE).write_text("{not json")

    with pytest.raises(json.JSONDecodeError):
        box.apply(box.rec("m", files=_a_file(box, "a")))

    assert not box.exists("a")
    assert box.hooks == []
    assert Path(engine.state.STATE_FILE).read_text() == "{not json"


def test_changes_survive_a_run_that_stops_before_the_hooks(box: harness.Box) -> None:
    a: str = box.path("a.conf")
    box.apply(box.rec("a", files={a: engine.File(content="x")}))

    with pytest.raises(RuntimeError):
        box.apply(box.rec("a", files={a: engine.File(content="y")}, actions={"on_change": _raise("stopped")}))

    # The file is in place now, so only the saved change can tell the hook about it.
    heard: harness.Rec = box.rec("a", files={a: engine.File(content="y")})
    box.apply(heard)

    assert heard.changes[0].files_changed(a)
