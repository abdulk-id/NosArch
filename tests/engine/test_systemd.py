"""The systemd step: which `systemctl` commands run, in what order, and what the engine remembers it enabled."""

from __future__ import annotations

import engine
import engine.command
import harness
import pytest
from engine.steps import systemd

STEPS: tuple[str] = ("systemd",)
RELOAD: list[str] = ["systemctl", "daemon-reload"]


def _user_reload(user: str) -> list[str]:
    return ["systemctl", "--user", "-M", f"{user}@", "daemon-reload"]


def test_new_units_are_enabled_in_one_command_and_a_second_run_only_reloads(box: harness.Box) -> None:
    names: list[str] = [f"{letter}.service" for letter in "hgfedcba"]

    def module() -> harness.Rec:
        return box.rec("m", units=set(names))

    box.apply(module(), steps=STEPS)

    # Sorted, so the same declaration is always the same command.
    assert box.argv == [["systemctl", "enable", *sorted(names)], RELOAD]
    assert box.state().systemd_units == sorted(names)  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(module(), steps=STEPS)

    assert box.argv == [RELOAD]


def test_a_dropped_unit_is_disabled_and_forgotten_even_if_systemctl_fails(box: harness.Box) -> None:
    box.apply(box.rec("m", units={"a.service", "b.service"}), steps=STEPS)
    box.commands.fail("systemctl", "disable")

    box.apply(box.rec("m", units={"a.service"}), steps=STEPS)

    assert box.argv == [["systemctl", "disable", "b.service"], RELOAD]
    assert box.state().systemd_units == ["a.service"]  # pyright: ignore[reportOptionalMemberAccess]


def test_a_failing_enable_fails_the_run_and_records_nothing(
    box: harness.Box, capsys: pytest.CaptureFixture[str]
) -> None:
    box.commands.fail("systemctl", "enable")

    with pytest.raises(engine.command.CommandFailedError):
        box.apply(box.rec("m", units={"good.service", "bad.service"}), steps=STEPS)

    assert box.hooks == ["before_update:m"]
    assert box.argv == [["systemctl", "enable", "bad.service", "good.service"]]
    assert box.state() is None
    assert "Running a systemd command failed" in capsys.readouterr().err


def test_user_units_go_through_the_users_manager_and_are_disabled_when_the_user_drops_them(box: harness.Box) -> None:
    box.apply(box.rec("m", user_units={"alice": {"x.service"}}), steps=STEPS)

    assert box.argv == [["systemctl", "--user", "-M", "alice@", "enable", "x.service"], RELOAD, _user_reload("alice")]

    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [["systemctl", "--user", "-M", "alice@", "disable", "x.service"], RELOAD, _user_reload("alice")]

    # The user stays in the state with nothing enabled, so its manager is still reloaded.
    box.apply(box.rec("m"), steps=STEPS)

    assert box.argv == [RELOAD, _user_reload("alice")]


def test_commands_run_in_a_fixed_order(box: harness.Box) -> None:
    box.apply(box.rec("m", units={"a.service"}, user_units={"alice": {"x.service"}}), steps=STEPS)

    box.apply(box.rec("m", units={"b.service"}, user_units={"alice": {"y.service"}}), steps=STEPS)

    assert box.argv == [
        ["systemctl", "enable", "b.service"],
        ["systemctl", "disable", "a.service"],
        ["systemctl", "--user", "-M", "alice@", "enable", "y.service"],
        ["systemctl", "--user", "-M", "alice@", "disable", "x.service"],
        RELOAD,
        _user_reload("alice"),
    ]


def test_units_of_a_module_that_is_removed_are_disabled_in_the_same_run(box: harness.Box) -> None:
    box.apply(box.rec("m", units={"a.service"}), box.rec("keep", units={"k.service"}), steps=STEPS)

    box.apply(box.rec("keep", units={"k.service"}), disabled=[box.rec("m")], steps=STEPS)

    assert ["systemctl", "disable", "a.service"] in box.argv
    assert box.state().systemd_units == ["k.service"]  # pyright: ignore[reportOptionalMemberAccess]


def test_decorated_methods_of_one_module_are_unioned(box: harness.Box) -> None:
    class Two(harness.Rec):
        @systemd.units
        def first(self) -> set[str]:
            return {"a.service"}

        @systemd.units
        def second(self) -> set[str]:
            return {"b.service"}

        @systemd.user_units
        def user_one(self) -> dict[str, set[str]]:
            return {"alice": {"x.service"}}

        @systemd.user_units
        def user_two(self) -> dict[str, set[str]]:
            return {"alice": {"y.service"}}

    box.apply(Two("m", box.log), steps=STEPS)

    # decman let the later method win a user's key. The units of both are wanted, so both are enabled.
    assert box.argv == [
        ["systemctl", "enable", "a.service", "b.service"],
        ["systemctl", "--user", "-M", "alice@", "enable", "x.service", "y.service"],
        RELOAD,
        _user_reload("alice"),
    ]


def test_a_dry_run_lists_the_units_and_runs_no_command(box: harness.Box, capsys: pytest.CaptureFixture[str]) -> None:
    box.apply(box.rec("m", units={"a.service"}, user_units={"alice": {"x.service"}}), steps=STEPS, dry_run=True)

    printed: str = capsys.readouterr().out
    assert box.argv == []
    assert box.state() is None
    assert "Enabling systemd units:\n    a.service" in printed
    assert "Enabling systemd units for alice:\n    x.service" in printed
