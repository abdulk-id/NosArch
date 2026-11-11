"""What a module is told changed: the `Changes` it gets, and how unit changes are detected."""

from __future__ import annotations

import harness
import pytest

import nosarch.engine


def _units(box: harness.Box, runs: list[set[str]]) -> list[list[str]]:
    """The hooks of each run, for a module `m` that declares `runs[i]` on run `i`."""
    result: list[list[str]] = []
    for units in runs:
        box.apply(box.rec("m", units=units), steps=("systemd",))
        result.append(box.hooks)
    return result


CHANGED: list[str] = ["before_update:m", "on_change:m", "after_update:m"]
QUIET: list[str] = ["before_update:m", "after_update:m"]


def test_a_module_is_changed_when_its_unit_set_differs(box: harness.Box) -> None:
    first, same, added, reordered, removed = _units(
        box, [{"a.service"}, {"a.service"}, {"a.service", "b.service"}, {"b.service", "a.service"}, set()]
    )

    assert first == ["before_update:m", "on_enable:m", "on_change:m", "after_update:m"]
    assert same == QUIET
    assert added == CHANGED
    assert reordered == QUIET
    assert removed == CHANGED


@pytest.mark.parametrize(
    ("before", "after", "changed"),
    [
        ({"alice": {"x.service"}}, {"alice": {"x.service"}}, False),
        ({"alice": {"x.service"}}, {"alice": {"x.service", "y.service"}}, True),
        ({"alice": {"x.service"}}, {"alice": {"x.service"}, "bob": {"z.service"}}, True),
        ({"alice": {"x.service"}, "bob": {"z.service"}}, {"alice": {"x.service"}}, True),
    ],
    ids=["same", "added unit", "added user", "removed user"],
)
def test_user_units_are_compared_per_user(
    box: harness.Box, before: dict[str, set[str]], after: dict[str, set[str]], changed: bool
) -> None:
    box.apply(box.rec("m", user_units=before), steps=("systemd",))
    box.apply(box.rec("m", user_units=after), steps=("systemd",))

    assert box.hooks == (CHANGED if changed else QUIET)


def test_on_change_is_told_which_units_were_added_and_removed(box: harness.Box) -> None:
    box.apply(box.rec("m", units={"a.service", "b.service"}), steps=("systemd",))

    module: harness.Rec = box.rec("m", units={"b.service", "c.service"})
    box.apply(module, steps=("systemd",))

    changes: nosarch.engine.Changes = module.changes[0]
    assert changes.added_pkgs["systemd"] == {"c.service"}
    assert changes.removed_pkgs["systemd"] == {"a.service"}
    assert changes.package_changed("a.service", kinds=("systemd",))
    assert not changes.package_changed("b.service")


def test_a_unit_declared_by_two_modules_stays_when_one_drops_it(box: harness.Box) -> None:
    box.apply(box.rec("x", units={"shared.service"}), box.rec("y", units={"shared.service"}), steps=("systemd",))

    box.apply(box.rec("x"), box.rec("y", units={"shared.service"}), steps=("systemd",))

    assert box.hooks == ["before_update:x", "before_update:y", "on_change:x", "after_update:x", "after_update:y"]
    assert box.argv == [["systemctl", "daemon-reload"]]
    assert box.state().systemd_units == ["shared.service"]  # pyright: ignore[reportOptionalMemberAccess]


def test_only_what_the_step_acted_on_counts_as_changed(box: harness.Box) -> None:
    # `--only files` never reports a unit change it did not make.
    box.apply(box.rec("m", units={"a.service"}), steps=("files", "systemd"), only=["files"])

    assert box.hooks == ["before_update:m", "on_enable:m", "after_update:m"]


# --- The Changes API --------------------------------------------------------------------------------------------------
def test_files_changed_matches_exact_paths() -> None:
    changes: nosarch.engine.Changes = nosarch.engine.Changes()
    changes.changed_files.add("/etc/a.conf")

    assert changes.files_changed("/etc/a.conf")
    assert changes.files_changed("/nope", "/etc/a.conf")
    assert not changes.files_changed("/etc")


def test_files_changed_in_dirs_compares_path_components() -> None:
    changes: nosarch.engine.Changes = nosarch.engine.Changes()
    changes.changed_files.add("/etc/systemd/system.conf.d/a.conf")

    assert changes.files_changed_in_dirs("/etc/systemd")
    assert changes.files_changed_in_dirs("/etc/systemd/system.conf.d")
    assert not changes.files_changed_in_dirs("/etc/systemd/system")


def test_changes_survive_a_round_trip_through_json() -> None:
    changes: nosarch.engine.Changes = nosarch.engine.Changes()
    changes.changed_files.add("/etc/a.conf")
    changes.added_pkgs["pacman"].add("git")
    changes.removed_pkgs["systemd"].add("a.service")

    again: nosarch.engine.Changes = nosarch.engine.Changes.from_json(changes.to_json())

    assert again.changed_files == {"/etc/a.conf"}
    assert again.added_pkgs["pacman"] == {"git"}
    assert again.removed_pkgs["systemd"] == {"a.service"}
    assert not nosarch.engine.Changes()
    assert again
