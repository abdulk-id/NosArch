"""The users step: the `useradd`, `usermod` and `userdel` it runs, and which accounts it considers its own."""

from __future__ import annotations

import harness
import pytest

import nosarch.engine
import nosarch.engine.command

STEPS: tuple[str, ...] = ("users", "files")


def _alice(accounts: harness.Accounts, groups: tuple[str, ...] = ("wheel",), shell: str = "/usr/bin/bash") -> None:
    accounts.add_group("wheel", 998)
    accounts.add_user("alice", 1000, 1000, "/home/alice", shell, groups=groups)


def test_a_missing_user_is_created_and_a_matching_one_is_left_alone(
    box: harness.Box, accounts: harness.Accounts
) -> None:
    _alice(accounts)
    declared: list[nosarch.engine.User] = [
        nosarch.engine.User("bob", group="alice", home="/home/bob", shell="/usr/bin/bash", groups=("wheel",)),
        nosarch.engine.User("alice", group="alice", home="/home/alice", shell="/usr/bin/bash", groups=("wheel",)),
    ]

    box.apply(users=declared, steps=STEPS)

    assert box.argv == [
        [
            "useradd",
            "--gid",
            "alice",
            "--create-home",
            "--home-dir",
            "/home/bob",
            "--shell",
            "/usr/bin/bash",
            "--groups",
            "wheel",
            "bob",
        ]
    ]
    assert accounts.members("wheel") == {"alice", "bob"}

    box.apply(users=declared, steps=STEPS)

    assert box.argv == []


def test_a_system_user_is_created_with_its_home_and_no_group(box: harness.Box, accounts: harness.Accounts) -> None:
    declared: list[nosarch.engine.User] = [
        nosarch.engine.User("aurbuilduser", home="/var/lib/aurbuilduser", system=True)
    ]

    box.apply(users=declared, steps=STEPS)
    assert box.argv == [["useradd", "--create-home", "--home-dir", "/var/lib/aurbuilduser", "--system", "aurbuilduser"]]

    box.apply(users=declared, steps=STEPS)
    assert box.argv == []


def test_a_users_own_group_is_made_by_useradd_and_any_other_group_must_exist(
    box: harness.Box, accounts: harness.Accounts
) -> None:
    with pytest.raises(nosarch.engine.command.CommandFailedError):
        box.apply(
            users=[nosarch.engine.User("bob", group="bob"), nosarch.engine.User("carol", group="staff")], steps=STEPS
        )

    assert box.argv == [["useradd", "--user-group", "bob"], ["useradd", "--gid", "staff", "carol"]]


def test_a_drifted_user_gets_one_usermod_with_only_the_differing_options(
    box: harness.Box, accounts: harness.Accounts
) -> None:
    _alice(accounts)

    box.apply(
        users=[
            nosarch.engine.User("alice", group="wheel", home="/home/alice", shell="/usr/bin/zsh", groups=("wheel",))
        ],
        steps=STEPS,
    )

    assert box.argv == [["usermod", "--gid", "wheel", "--shell", "/usr/bin/zsh", "alice"]]


def test_declared_groups_replace_the_supplementary_groups(box: harness.Box, accounts: harness.Accounts) -> None:
    accounts.add_group("docker", 970)
    accounts.add_group("video", 971)
    _alice(accounts, groups=("wheel", "docker", "video"))
    declared: list[nosarch.engine.User] = [nosarch.engine.User("alice", group="alice", groups=("alice", "wheel"))]

    box.apply(users=declared, steps=STEPS)

    assert box.argv == [["usermod", "--groups", "alice,wheel", "alice"]]
    assert accounts.members("docker") == set()
    assert accounts.members("video") == set()

    box.apply(users=declared, steps=STEPS)

    assert box.argv == []


def test_a_group_that_a_package_creates_is_added_once_the_steps_have_run(
    box: harness.Box, accounts: harness.Accounts, capsys: pytest.CaptureFixture[str]
) -> None:
    declared: list[nosarch.engine.User] = [nosarch.engine.User("bob", groups=("libvirt",))]

    # libvirt does not exist when the user is created, as on a first run where its package is installed later.
    box.apply(
        box.rec("m", actions={"before_update": lambda: accounts.add_group("libvirt", 900)}), users=declared, steps=STEPS
    )

    assert box.argv == [["useradd", "bob"], ["usermod", "--groups", "libvirt", "bob"]]
    assert accounts.members("libvirt") == {"bob"}
    assert "do not exist" not in capsys.readouterr().err


def test_a_group_that_never_appears_is_a_warning(
    box: harness.Box, accounts: harness.Accounts, capsys: pytest.CaptureFixture[str]
) -> None:
    box.apply(users=[nosarch.engine.User("bob", groups=("nosuchgroup",))], steps=STEPS)

    assert "Groups for bob do not exist: nosuchgroup" in capsys.readouterr().err


def test_users_exist_before_any_hook_runs(box: harness.Box, accounts: harness.Accounts) -> None:
    seen: list[bool] = []
    module: harness.Rec = box.rec("later", actions={"before_update": lambda: seen.append(accounts.has_user("bob"))})

    box.apply(module, users=[nosarch.engine.User("bob")], steps=STEPS)

    assert seen == [True]


def test_a_failing_useradd_fails_the_run_before_any_hook_or_step(box: harness.Box, accounts: harness.Accounts) -> None:
    box.commands.fail("useradd")

    with pytest.raises(nosarch.engine.command.CommandFailedError):
        box.apply(
            box.rec("m", files={box.path("a"): nosarch.engine.File(content="a\n")}),
            users=[nosarch.engine.User("bob")],
            steps=STEPS,
        )

    assert box.hooks == []
    assert not box.exists("a")
    assert not accounts.has_user("bob")


def test_only_accounts_the_engine_created_are_deleted(box: harness.Box, accounts: harness.Accounts) -> None:
    # Only an account the engine created is deleted, never the login user it was only told about.
    _alice(accounts)

    box.apply(
        users=[nosarch.engine.User("bob"), nosarch.engine.User("alice", group="alice", groups=("wheel",))], steps=STEPS
    )
    assert box.state().created_users == ["bob"]  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(steps=STEPS)

    assert box.argv == [["userdel", "bob"]]
    assert accounts.has_user("alice")
    assert not accounts.has_user("bob")
    assert box.state().created_users == []  # pyright: ignore[reportOptionalMemberAccess]


def test_a_dry_run_does_not_touch_users(box: harness.Box, accounts: harness.Accounts) -> None:
    _alice(accounts, shell="/usr/bin/bash")

    box.apply(
        users=[
            nosarch.engine.User("bob"),
            nosarch.engine.User("alice", group="alice", shell="/usr/bin/zsh", groups=("wheel",)),
        ],
        steps=STEPS,
        dry_run=True,
    )

    assert box.argv == []
    assert not accounts.has_user("bob")
    assert box.state() is None


def test_a_dry_run_where_a_files_owner_does_not_exist_yet_reports_it(
    box: harness.Box, accounts: harness.Accounts, capsys: pytest.CaptureFixture[str]
) -> None:
    # Owners are resolved at the files step, so a dry run can say the user is coming.
    module: harness.Rec = box.rec("m", files={box.path("a.conf"): nosarch.engine.File(content="x\n", owner="bob")})

    box.apply(module, users=[nosarch.engine.User("bob")], steps=STEPS, dry_run=True)

    assert f"{box.path('a.conf')} (owner does not exist yet)" in capsys.readouterr().out
    assert not box.exists("a.conf")


def test_a_file_whose_owner_never_exists_fails_a_real_run(box: harness.Box, accounts: harness.Accounts) -> None:
    module: harness.Rec = box.rec(
        "m", files={box.path("a.conf"): nosarch.engine.File(content="x\n", owner="nosuchuser")}
    )

    with pytest.raises(nosarch.engine.command.AccountNotFoundError, match="The user 'nosuchuser' doesn't exist"):
        box.apply(module, steps=STEPS)

    assert not box.exists("a.conf")
