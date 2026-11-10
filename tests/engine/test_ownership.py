"""
Owners and groups, and running as another user. They need root, so `mise run test-engine-root` runs them in a user
namespace where the test process is root and the ids 1 to 65536 exist. Nothing here touches the real machine.
"""

from __future__ import annotations

import os

import engine
import harness
import pytest

pytestmark = pytest.mark.needs_root

ALICE: int = 1000
WHEEL: int = 998


@pytest.fixture(autouse=True)
def _alice(accounts: harness.Accounts) -> None:
    accounts.add_user("alice", ALICE, ALICE, "/home/alice")
    accounts.add_group("wheel", WHEEL)


def _owner(box: harness.Box, relative: str) -> tuple[int, int]:
    status: os.stat_result = os.lstat(box.path(relative))
    return status.st_uid, status.st_gid


def test_parent_directories_are_owned_like_the_file(box: harness.Box) -> None:
    box.apply(
        box.rec(
            "m",
            files={
                box.path("home/x/y/z.conf"): engine.File(content="z\n", owner="alice"),
                box.path("etc/p/q/r.conf"): engine.File(content="r\n"),
            },
        )
    )

    assert _owner(box, "home/x") == (ALICE, ALICE)
    assert _owner(box, "home/x/y/z.conf") == (ALICE, ALICE)
    assert _owner(box, "etc/p/q") == (0, 0)


def test_owner_drift_is_healed_and_counts_as_a_change(box: harness.Box) -> None:
    def module() -> harness.Rec:
        return box.rec("m", files={box.path("a.conf"): engine.File(content="x\n", owner="alice")})

    box.apply(module())
    os.chown(box.path("a.conf"), 0, 0)
    box.apply(module())

    assert _owner(box, "a.conf") == (ALICE, ALICE)
    assert box.hooks == ["before_update:m", "on_change:m", "after_update:m"]


def test_a_file_with_no_owner_keeps_the_owner_of_the_file_it_replaces(box: harness.Box) -> None:
    box.write("old.conf", "old\n", mode=0o600)
    os.chown(box.path("old.conf"), ALICE, ALICE)

    box.apply(
        box.rec(
            "m",
            files={
                box.path("old.conf"): engine.File(content="new\n"),
                box.path("new.conf"): engine.File(content="new\n"),
            },
        )
    )

    assert _owner(box, "old.conf") == (ALICE, ALICE)
    assert box.mode("old.conf") == 0o644
    assert box.read("old.conf") == "new\n"
    assert _owner(box, "new.conf") == (0, 0)


def test_an_explicit_group_applies_to_the_file_and_the_directories_made_for_it(box: harness.Box) -> None:
    box.apply(box.rec("m", files={box.path("g/a.conf"): engine.File(content="x\n", owner="alice", group="wheel")}))

    assert _owner(box, "g/a.conf") == (ALICE, WHEEL)
    assert _owner(box, "g") == (ALICE, WHEEL)


def test_a_directory_deploys_every_file_with_its_owner_and_mode(box: harness.Box) -> None:
    box.write("tree/a.txt", "a\n")
    box.write("tree/sub/b.txt", "b\n")

    box.apply(
        box.rec(
            "m",
            directories={
                box.path("out"): engine.Directory(source_directory=box.path("tree"), owner="alice", permissions=0o600)
            },
        )
    )

    assert _owner(box, "out/a.txt") == (ALICE, ALICE)
    assert box.mode("out/sub/b.txt") == 0o600
    assert _owner(box, "out/sub") == (ALICE, ALICE)


def test_a_symlink_is_owned_itself_and_so_are_its_parents(box: harness.Box) -> None:
    box.apply(
        box.rec(
            "m",
            symlinks={box.path("home/.x/y/link"): engine.Symlink("/etc/target", owner="alice"), box.path("snap"): "/s"},
        )
    )

    assert _owner(box, "home/.x/y/link") == (ALICE, ALICE)
    assert _owner(box, "home/.x") == (ALICE, ALICE)
    assert _owner(box, "snap") == (0, 0)


def test_a_file_owned_by_a_user_created_in_the_same_run(box: harness.Box) -> None:
    module: harness.Rec = box.rec("m", files={box.path("bob.conf"): engine.File(content="x\n", owner="bob")})

    box.apply(module, users=[engine.User("bob")], steps=("users", "files"))

    assert _owner(box, "bob.conf")[0] > 0
    assert box.read("bob.conf") == "x\n"


def test_a_command_can_run_as_another_user(box: harness.Box, accounts: harness.Accounts) -> None:
    box_output: str = harness.real_run(["id", "-u"], user="alice", capture=True)

    assert box_output == f"{ALICE}\n"
