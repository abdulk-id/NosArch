"""Hooks: when `on_enable`, `on_change` and `on_disable` fire, and what a failure leaves behind."""

from __future__ import annotations

from collections.abc import Callable

import harness
import pytest

import nosarch.engine


def _raise(message: str) -> Callable[[], None]:
    def raiser() -> None:
        raise RuntimeError(message)

    return raiser


def _a_file(box: harness.Box, name: str) -> dict[str, nosarch.engine.File]:
    return {box.path(name): nosarch.engine.File(content=f"{name}\n")}


def test_on_enable_fires_once_after_the_steps_and_only_for_a_new_module(box: harness.Box) -> None:
    def m() -> harness.Rec:
        return box.rec("m", files=_a_file(box, "a"), units={"a.service"})

    box.apply(m(), steps=("files", "systemd"))
    assert box.log.index("cmd systemctl enable a.service") < box.log.index("on_enable:m") < box.log.index("on_change:m")

    box.apply(m(), steps=("files", "systemd"))
    assert "on_enable:m" not in box.hooks

    box.apply(m(), box.rec("n", files=_a_file(box, "n")), steps=("files", "systemd"))
    assert "on_enable:n" in box.hooks and "on_change:n" in box.hooks
    assert "on_enable:m" not in box.hooks and "on_change:m" not in box.hooks


# --- Disabling --------------------------------------------------------------------------------------------------------
def test_a_module_that_is_switched_off_runs_on_disable_before_the_steps(box: harness.Box) -> None:
    box.apply(
        box.rec("m", files=_a_file(box, "m"), units={"m.service"}),
        box.rec("other", files=_a_file(box, "o")),
        steps=("files", "systemd"),
    )

    box.apply(box.rec("other", files=_a_file(box, "o")), disabled=[box.rec("m")], steps=("files", "systemd"))

    # The module's own files are still there for on_disable, then the files step removes them.
    assert box.log[:3] == ["before_update:other", "on_disable:m", "cmd systemctl disable m.service"]
    assert not box.exists("m")
    assert box.state().enabled_modules == ["other"]  # pyright: ignore[reportOptionalMemberAccess]


def test_a_module_switched_off_in_the_same_run_that_removes_its_files_hears_nothing_more(box: harness.Box) -> None:
    box.apply(box.rec("m", files=_a_file(box, "m")), box.rec("other"))
    box.apply(box.rec("other"), disabled=[box.rec("m")])

    assert "on_change:m" not in box.hooks
    assert "on_enable:m" not in box.hooks


def test_several_modules_are_disabled_in_the_order_they_were_enabled(box: harness.Box) -> None:
    box.apply(box.rec("b"), box.rec("a"), box.rec("c"))

    box.apply(box.rec("other"), disabled=[box.rec("a"), box.rec("b"), box.rec("c")])

    assert box.hooks == [
        "before_update:other",
        "on_disable:b",
        "on_disable:a",
        "on_disable:c",
        "on_enable:other",
        "after_update:other",
    ]


def test_a_failing_on_disable_stops_the_run_and_is_retried_next_time(box: harness.Box) -> None:
    box.apply(box.rec("m"))

    with pytest.raises(RuntimeError):
        box.apply(
            box.rec("other", files=_a_file(box, "o")), disabled=[box.rec("m", actions={"on_disable": _raise("x")})]
        )

    assert box.hooks == ["before_update:other", "on_disable:m"]
    assert not box.exists("o")
    assert box.state().enabled_modules == ["m"]  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(box.rec("other", files=_a_file(box, "o")), disabled=[box.rec("m")])

    assert "on_disable:m" in box.hooks
    assert box.state().enabled_modules == ["other"]  # pyright: ignore[reportOptionalMemberAccess]


def test_a_dry_run_and_no_hooks_leave_a_removed_module_enabled(box: harness.Box) -> None:
    box.apply(box.rec("m"))

    box.apply(box.rec("other"), disabled=[box.rec("m")], dry_run=True)
    assert box.hooks == []
    assert box.state().enabled_modules == ["m"]  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(box.rec("other"), disabled=[box.rec("m")], no_hooks=True)
    assert box.hooks == []
    assert box.state().enabled_modules == ["m"]  # pyright: ignore[reportOptionalMemberAccess]


def test_a_module_that_is_gone_from_the_code_is_forgotten_with_a_warning(
    box: harness.Box, capsys: pytest.CaptureFixture[str]
) -> None:
    box.apply(box.rec("m"), box.rec("keep"))

    # on_disable only runs for a module still registered as disabled. One gone from the code is forgotten.
    box.apply(box.rec("keep"))

    assert box.hooks == ["before_update:keep", "after_update:keep"]
    assert "Module m no longer exists" in capsys.readouterr().err
    assert box.state().enabled_modules == ["keep"]  # pyright: ignore[reportOptionalMemberAccess]


def test_adding_a_removed_module_back_fires_on_enable_again(box: harness.Box) -> None:
    box.apply(box.rec("m"), box.rec("keep"))
    box.apply(box.rec("keep"))

    box.apply(box.rec("m"), box.rec("keep"))

    assert "on_enable:m" in box.hooks
