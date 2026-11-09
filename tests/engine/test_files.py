"""The files step: what gets written, what counts as a change, and what is removed."""

from __future__ import annotations

import os
from pathlib import Path

import engine
import engine.fs
import engine.steps.files
import harness
import pytest


# --- Writing ----------------------------------------------------------------------------------------------------------
def test_new_file_is_created_and_reported(box: harness.Box) -> None:
    module: harness.Rec = box.rec("m", files={box.path("etc/a.conf"): engine.File(content="a\n")})
    box.apply(module)

    assert box.read("etc/a.conf") == "a\n"
    assert box.mode("etc/a.conf") == 0o644
    assert box.hooks == ["before_update:m", "on_enable:m", "on_change:m", "after_update:m"]
    assert module.changes[0].files_changed(box.path("etc/a.conf"))


def test_source_file_is_copied(box: harness.Box) -> None:
    source: str = box.write("src/a.txt", "from source\n")
    box.apply(box.rec("m", files={box.path("etc/a.conf"): engine.File(source_file=source)}))

    assert box.read("etc/a.conf") == "from source\n"


def test_empty_content_creates_an_empty_file(box: harness.Box) -> None:
    module: harness.Rec = box.rec("m", files={box.path("etc/empty"): engine.File(content="")})
    box.apply(module)

    assert (box.root / "etc/empty").stat().st_size == 0
    assert module.changes


def test_a_file_needs_a_source_or_content_but_not_both() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        engine.File()
    with pytest.raises(ValueError, match="exactly one"):
        engine.File(source_file="a", content="b")


def test_an_unchanged_file_is_not_rewritten_or_reported(box: harness.Box) -> None:
    def module() -> harness.Rec:
        return box.rec("m", files={box.path("etc/a.conf"): engine.File(content="a\n")})

    box.apply(module())
    before: os.stat_result = os.stat(box.path("etc/a.conf"))
    box.apply(module())
    after: os.stat_result = os.stat(box.path("etc/a.conf"))

    assert box.hooks == ["before_update:m", "after_update:m"]
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)


@pytest.mark.parametrize("permissions", [0o755, 0o600, 0o4755])
def test_exact_permissions_are_applied(box: harness.Box, permissions: int) -> None:
    box.apply(box.rec("m", files={box.path("etc/f"): engine.File(content="x", permissions=permissions)}))

    assert box.mode("etc/f") == permissions


def test_mode_drift_is_healed_and_counts_as_a_change(box: harness.Box) -> None:
    # A hook that reloads a service has to hear about a file that was put back.
    def module() -> harness.Rec:
        return box.rec("m", files={box.path("etc/a.conf"): engine.File(content="x\n")})

    box.apply(module())
    os.chmod(box.path("etc/a.conf"), 0o600)
    changed: harness.Rec = module()
    box.apply(changed)

    assert box.mode("etc/a.conf") == 0o644
    assert box.hooks == ["before_update:m", "on_change:m", "after_update:m"]
    assert changed.changes[0].files_changed(box.path("etc/a.conf"))


def test_missing_parent_directories_are_created_and_not_tracked(box: harness.Box) -> None:
    target: str = box.path("etc/p/q/r.conf")
    box.apply(box.rec("m", files={target: engine.File(content="r\n")}))

    assert box.mode("etc/p/q") == 0o755
    assert box.state().files == {"m": [target]}  # pyright: ignore[reportOptionalMemberAccess]

    box.apply(box.rec("m"))

    assert not box.exists("etc/p/q/r.conf")
    assert box.exists("etc/p/q")


def test_a_changed_file_is_replaced_atomically(box: harness.Box) -> None:
    # A reader of the target never sees half a file, and a hard link keeps the old content.
    box.apply(box.rec("m", files={box.path("etc/a.conf"): engine.File(content="one\n")}))
    os.link(box.path("etc/a.conf"), box.path("etc/hardlink"))

    box.apply(box.rec("m", files={box.path("etc/a.conf"): engine.File(content="two\n")}))

    assert box.read("etc/a.conf") == "two\n"
    assert box.read("etc/hardlink") == "one\n"


def test_a_file_declared_on_a_symlink_replaces_the_link(box: harness.Box) -> None:
    box.write("etc/real", "old\n")
    os.symlink(box.path("etc/real"), box.path("etc/link"))

    box.apply(box.rec("m", files={box.path("etc/link"): engine.File(content="new\n")}))

    assert not os.path.islink(box.path("etc/link"))
    assert box.read("etc/link") == "new\n"
    assert box.read("etc/real") == "old\n"


def test_a_first_run_overwrites_declared_files_and_leaves_the_rest(box: harness.Box) -> None:
    box.write("etc/a", "old\n")
    box.write("etc/unmanaged", "mine\n")

    box.apply(box.rec("m", files={box.path("etc/a"): engine.File(content="new\n")}))

    assert box.read("etc/a") == "new\n"
    assert box.read("etc/unmanaged") == "mine\n"


# --- Variables and binary files ---------------------------------------------------------------------------------------
def test_variables_belong_to_their_module(box: harness.Box) -> None:
    box.apply(
        box.rec(
            "a", files={box.path("a"): engine.File(content="%V% %UNSET%\n")}, variables={"%V%": "a", "%UNUSED%": "q"}
        ),
        box.rec("b", files={box.path("b"): engine.File(content="%V%\n")}, variables={"%V%": "b"}),
    )

    assert box.read("a") == "a %UNSET%\n"
    assert box.read("b") == "b\n"


def test_variable_values_are_inserted_literally(box: harness.Box) -> None:
    box.apply(
        box.rec(
            "m", files={box.path("a"): engine.File(content="[%V%]\n")}, variables={"%V%": "a.*\\1 \"q\" 'r'\nnext"}
        ),
        box.rec("e", files={box.path("e"): engine.File(content="[%V%]\n")}, variables={"%V%": ""}),
    )

    assert box.read("a") == "[a.*\\1 \"q\" 'r'\nnext]\n"
    assert box.read("e") == "[]\n"


def test_variables_are_replaced_one_after_another(box: harness.Box) -> None:
    # A value that contains another key is replaced again, if that key comes later.
    box.apply(
        box.rec(
            "forward", files={box.path("forward"): engine.File(content="%A%\n")}, variables={"%A%": "%B%", "%B%": "x"}
        ),
        box.rec(
            "reverse", files={box.path("reverse"): engine.File(content="%A%\n")}, variables={"%B%": "x", "%A%": "%B%"}
        ),
    )

    assert box.read("forward") == "x\n"
    assert box.read("reverse") == "%B%\n"


def test_a_changed_variable_rewrites_the_file_and_reports_it(box: harness.Box) -> None:
    def module(value: str) -> harness.Rec:
        return box.rec("m", files={box.path("a"): engine.File(content="%V%\n")}, variables={"%V%": value})

    box.apply(module("a"))
    box.apply(module("b"))

    assert box.read("a") == "b\n"
    assert box.hooks == ["before_update:m", "on_change:m", "after_update:m"]


def test_variables_are_read_after_every_before_update(box: harness.Box) -> None:
    marker: str = box.path("marker")

    class Reader(harness.Rec):
        def file_variables(self) -> dict[str, str]:
            return {"%V%": Path(marker).read_text()}

    def make_marker() -> None:
        Path(marker).write_text("made-by-hook")

    box.apply(
        box.rec("maker", actions={"before_update": make_marker}),
        Reader("reader", box.log, files={box.path("a"): engine.File(content="%V%\n")}),
    )

    assert box.read("a") == "made-by-hook\n"


def test_text_without_variables_is_copied_byte_for_byte(box: harness.Box) -> None:
    source: str = box.write("src/crlf.txt", b"a\r\nb %Z%\r\n")
    box.apply(
        box.rec("plain", files={box.path("plain"): engine.File(source_file=source)}),
        box.rec("vars", files={box.path("vars"): engine.File(source_file=source)}, variables={"%Z%": "z"}),
    )

    assert (box.root / "plain").read_bytes() == b"a\r\nb %Z%\r\n"
    assert (box.root / "vars").read_bytes() == b"a\nb z\n"


def test_binary_files_are_never_substituted(box: harness.Box) -> None:
    template: str = box.write("src/tpl.txt", "value=%X%\n")
    box.apply(
        box.rec(
            "m",
            files={
                box.path("bin1"): engine.File(source_file=template, bin_file=True),
                box.path("bin2"): engine.File(content="é %X%", bin_file=True),
                box.path("bin3"): engine.File(content="é", bin_file=True, encoding="latin-1"),
                box.path("text"): engine.File(source_file=template),
            },
            variables={"%X%": "y"},
        )
    )

    assert box.read("bin1") == "value=%X%\n"
    assert box.read("bin2") == "é %X%"
    assert (box.root / "bin3").read_bytes() == b"\xe9"
    assert box.read("text") == "value=y\n"


# --- Directories ------------------------------------------------------------------------------------------------------
def test_directory_deploys_files_only_dotfiles_included(box: harness.Box) -> None:
    box.write("tree/a.txt", "a\n")
    box.write("tree/sub/b.txt", "b\n")
    box.write("tree/.hidden", "h\n")
    (box.root / "tree/empty").mkdir()

    box.apply(
        box.rec(
            "m", directories={box.path("out"): engine.Directory(source_directory=box.path("tree"), permissions=0o600)}
        )
    )

    assert box.read("out/a.txt") == "a\n"
    assert box.read("out/sub/b.txt") == "b\n"
    assert box.read("out/.hidden") == "h\n"
    assert box.mode("out/a.txt") == 0o600
    assert box.mode("out/sub") == 0o755
    assert not box.exists("out/empty")


def test_directory_text_files_are_substituted_unless_bin_files(box: harness.Box) -> None:
    box.write("tree/a.txt", "value=%V%\n")
    box.apply(
        box.rec(
            "m",
            directories={
                box.path("text"): engine.Directory(source_directory=box.path("tree")),
                box.path("binary"): engine.Directory(source_directory=box.path("tree"), bin_files=True),
            },
            variables={"%V%": "v"},
        )
    )

    assert box.read("text/a.txt") == "value=v\n"
    assert box.read("binary/a.txt") == "value=%V%\n"


def test_directory_follows_its_source(box: harness.Box) -> None:
    box.write("tree/keep.txt", "keep\n")
    box.write("tree/edit.txt", "one\n")
    box.write("tree/gone.txt", "gone\n")

    def module() -> harness.Rec:
        return box.rec("m", directories={box.path("out"): engine.Directory(source_directory=box.path("tree"))})

    box.apply(module())
    box.write("tree/edit.txt", "two\n")
    box.write("tree/new.txt", "new\n")
    os.remove(box.path("tree/gone.txt"))
    changed: harness.Rec = module()
    box.apply(changed)

    assert box.read("out/edit.txt") == "two\n"
    assert box.read("out/new.txt") == "new\n"
    assert box.read("out/keep.txt") == "keep\n"
    assert not box.exists("out/gone.txt")
    assert changed.changes[0].changed_files == {box.path(f"out/{name}") for name in ("edit.txt", "new.txt", "gone.txt")}

    box.apply(module())

    assert box.hooks == ["before_update:m", "after_update:m"]


def test_directory_with_a_missing_source_fails_the_run(box: harness.Box) -> None:
    module: harness.Rec = box.rec(
        "m", directories={box.path("out"): engine.Directory(source_directory=box.path("nosuchdir"))}
    )

    with pytest.raises(engine.fs.InstallError, match="Source directory doesn't exist"):
        box.apply(module)

    assert box.hooks == ["before_update:m"]


def test_directory_copies_a_linked_file_and_ignores_a_linked_directory(box: harness.Box) -> None:
    box.write("tree/a.txt", "a\n")
    box.write("tree/sub/b.txt", "b\n")
    os.symlink(box.path("tree/a.txt"), box.path("tree/linkfile"))
    os.symlink(box.path("tree/sub"), box.path("tree/linkdir"))

    box.apply(box.rec("m", directories={box.path("out"): engine.Directory(source_directory=box.path("tree"))}))

    assert not os.path.islink(box.path("out/linkfile"))
    assert box.read("out/linkfile") == "a\n"
    assert box.read("out/sub/b.txt") == "b\n"
    assert not box.exists("out/linkdir")


def test_binary_files_in_a_directory_need_bin_files_once_the_module_has_variables(box: harness.Box) -> None:
    image: bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\xff"
    box.write("src/wall/1.jpg", image)
    source: str = box.path("src/wall")

    box.apply(box.rec("m", directories={box.path("plain"): engine.Directory(source_directory=source)}))
    assert (box.root / "plain/1.jpg").read_bytes() == image

    with pytest.raises(engine.fs.InstallError, match="Unicode decoding failed"):
        box.apply(
            box.rec(
                "m", directories={box.path("text"): engine.Directory(source_directory=source)}, variables={"%V%": "v"}
            )
        )

    box.apply(
        box.rec(
            "m",
            directories={box.path("binary"): engine.Directory(source_directory=source, bin_files=True)},
            variables={"%V%": "v"},
        )
    )
    assert (box.root / "binary/1.jpg").read_bytes() == image


# --- Symlinks ---------------------------------------------------------------------------------------------------------
def test_symlink_is_created_at_the_literal_target_and_dangling_is_fine(box: harness.Box) -> None:
    def module() -> harness.Rec:
        return box.rec("m", symlinks={box.path("snap"): "/var/lib/snapd/snap"})

    box.apply(module())

    assert os.readlink(box.path("snap")) == "/var/lib/snapd/snap"
    assert box.hooks[2] == "on_change:m"

    box.apply(module())

    assert box.hooks == ["before_update:m", "after_update:m"]


def test_wrong_link_and_plain_file_are_replaced_and_a_right_link_is_left(box: harness.Box) -> None:
    box.write("p/plain", "x\n")
    os.symlink("/old", box.path("p/wrong"))
    os.symlink("/new", box.path("p/right"))
    module: harness.Rec = box.rec(
        "m", symlinks={box.path("p/wrong"): "/new", box.path("p/plain"): "/new", box.path("p/right"): "/new"}
    )

    box.apply(module)

    assert os.readlink(box.path("p/wrong")) == "/new"
    assert os.readlink(box.path("p/plain")) == "/new"
    assert module.changes[0].changed_files == {box.path("p/wrong"), box.path("p/plain")}


def test_link_targets_are_compared_as_strings(box: harness.Box) -> None:
    box.write("p/real", "x\n")
    os.symlink("real", box.path("p/link"))
    module: harness.Rec = box.rec("m", symlinks={box.path("p/link"): box.path("p/real")})

    box.apply(module)

    assert os.readlink(box.path("p/link")) == box.path("p/real")
    assert module.changes


def test_a_directory_at_the_link_path_fails_the_run(box: harness.Box) -> None:
    (box.root / "p/dir").mkdir(parents=True)

    with pytest.raises(engine.fs.InstallError, match="Failed to install symlink"):
        box.apply(box.rec("m", symlinks={box.path("p/dir"): "/new"}))


def test_an_undeclared_link_is_removed_but_not_its_target(box: harness.Box) -> None:
    real: str = box.path("p/real")
    box.apply(box.rec("m", files={real: engine.File(content="x\n")}, symlinks={box.path("p/link"): real}))
    box.apply(box.rec("m", files={real: engine.File(content="x\n")}))

    assert not box.exists("p/link")
    assert box.read("p/real") == "x\n"


# --- Failures ---------------------------------------------------------------------------------------------------------
def test_a_file_whose_target_is_a_directory_fails_the_run(box: harness.Box) -> None:
    (box.root / "p/d").mkdir(parents=True)

    with pytest.raises(engine.fs.InstallError, match="Failed to install file"):
        box.apply(box.rec("m", files={box.path("p/d"): engine.File(content="x\n")}))

    assert box.hooks == ["before_update:m"]


def test_invalid_utf8_in_a_text_file_with_variables_fails_the_run(box: harness.Box) -> None:
    bad: str = box.write("src/bad.bin", b"\xff")
    module: harness.Rec = box.rec(
        "m",
        files={
            box.path("first.conf"): engine.File(content="first\n"),
            box.path("bad.conf"): engine.File(source_file=bad),
            box.path("last.conf"): engine.File(content="last\n"),
        },
        variables={"%Z%": "z"},
    )

    with pytest.raises(engine.fs.InstallError, match="Unicode decoding failed"):
        box.apply(module)

    assert box.read("first.conf") == "first\n"
    assert not box.exists("last.conf")
    assert box.hooks == ["before_update:m"]


def test_a_missing_source_stops_the_step_and_removes_nothing(box: harness.Box) -> None:
    box.apply(
        box.rec("m", files={box.path("p/a"): engine.File(content="a1\n"), box.path("p/b"): engine.File(content="b\n")})
    )

    failing: harness.Rec = box.rec(
        "m",
        files={
            box.path("p/a"): engine.File(content="a2\n"),
            box.path("p/c"): engine.File(source_file=box.path("missing")),
            box.path("p/d"): engine.File(content="d\n"),
        },
    )
    with pytest.raises(engine.fs.InstallError, match="Source file doesn't exist"):
        box.apply(failing)

    assert box.read("p/a") == "a2\n"
    assert box.read("p/b") == "b\n"
    assert not box.exists("p/d")
    assert box.state().files == {"m": [box.path("p/a"), box.path("p/b")]}  # pyright: ignore[reportOptionalMemberAccess]


def test_two_modules_cannot_declare_one_path(box: harness.Box) -> None:
    same: str = box.path("same")

    with pytest.raises(engine.steps.files.DuplicateTargetError, match="declared by both a and b"):
        box.apply(
            box.rec("a", files={same: engine.File(content="x")}), box.rec("b", files={same: engine.File(content="y")})
        )


# --- Tracking and removal ---------------------------------------------------------------------------------------------
def test_an_undeclared_file_is_removed_and_its_module_hears_about_it(box: harness.Box) -> None:
    a: str = box.path("p/a")
    b: str = box.path("p/b")
    box.apply(box.rec("m", files={a: engine.File(content="a\n"), b: engine.File(content="b\n")}))

    module: harness.Rec = box.rec("m", files={a: engine.File(content="a\n")})
    box.apply(module)

    assert not box.exists("p/b")
    assert box.exists("p")
    assert module.changes[0].changed_files == {b}
    assert box.state().files == {"m": [a]}  # pyright: ignore[reportOptionalMemberAccess]


def test_a_file_that_moves_between_modules_is_not_removed(box: harness.Box) -> None:
    moved: str = box.path("p/moved")
    box.apply(box.rec("x", files={moved: engine.File(content="m\n")}), box.rec("y"))
    box.apply(box.rec("x"), box.rec("y", files={moved: engine.File(content="m\n")}))

    assert box.read("p/moved") == "m\n"
    assert box.state().files == {"y": [moved]}  # pyright: ignore[reportOptionalMemberAccess]


def test_removing_a_file_that_is_already_gone_is_not_a_failure(
    box: harness.Box, capsys: pytest.CaptureFixture[str]
) -> None:
    a: str = box.path("p/a")
    b: str = box.path("p/b")
    box.apply(box.rec("m", files={a: engine.File(content="a\n"), b: engine.File(content="b\n")}))
    os.remove(b)

    box.apply(box.rec("m", files={a: engine.File(content="a\n")}))

    assert "Could not remove" not in capsys.readouterr().err
    assert box.state().files == {"m": [a]}  # pyright: ignore[reportOptionalMemberAccess]


def test_a_directory_where_a_managed_file_was_is_left_alone(
    box: harness.Box, capsys: pytest.CaptureFixture[str]
) -> None:
    target: str = box.path("p/a")
    box.apply(box.rec("m", files={target: engine.File(content="a\n")}))
    os.remove(target)
    os.mkdir(target)
    box.write("p/a/mine.txt", "mine\n")

    module: harness.Rec = box.rec("m")
    box.apply(module)

    assert box.read("p/a/mine.txt") == "mine\n"
    assert "Could not remove" not in capsys.readouterr().err
    assert not module.changes


def test_a_run_that_skips_the_files_step_removes_nothing(box: harness.Box) -> None:
    a: str = box.path("p/a")
    b: str = box.path("p/b")
    steps: tuple[str, str] = ("files", "systemd")
    box.apply(box.rec("m", files={a: engine.File(content="a\n"), b: engine.File(content="b\n")}), steps=steps)

    box.apply(box.rec("m", files={a: engine.File(content="a\n")}), steps=steps, only=["systemd"])

    assert box.exists("p/b")
    assert box.state().files == {"m": [a, b]}  # pyright: ignore[reportOptionalMemberAccess]


# --- Dry runs ---------------------------------------------------------------------------------------------------------
def test_a_dry_run_changes_nothing(box: harness.Box, capsys: pytest.CaptureFixture[str]) -> None:
    box.write("p/changed", "old\n")
    box.write("p/same", "same\n")
    box.write("tree/a.txt", "a\n")

    box.apply(
        box.rec(
            "m",
            files={
                box.path("p/new"): engine.File(content="new\n"),
                box.path("p/changed"): engine.File(content="new\n"),
                box.path("p/same"): engine.File(content="same\n"),
            },
            symlinks={box.path("p/link"): "/x"},
            directories={box.path("p/dir"): engine.Directory(source_directory=box.path("tree"))},
        ),
        dry_run=True,
    )

    assert not box.exists("p/new")
    assert not box.exists("p/link")
    assert not box.exists("p/dir")
    assert box.read("p/changed") == "old\n"
    assert box.hooks == []
    assert box.state() is None
    assert "Updated files" in capsys.readouterr().out


def test_a_dry_run_lists_what_a_real_run_would_change(box: harness.Box, capsys: pytest.CaptureFixture[str]) -> None:
    box.write("p/mode", "x\n", mode=0o600)
    os.symlink("/old", box.path("p/wrong"))
    box.write("tree/a.txt", "a\n")

    box.apply(
        box.rec(
            "m",
            files={box.path("p/mode"): engine.File(content="x\n")},
            symlinks={box.path("p/wrong"): "/new"},
            directories={box.path("p/dir"): engine.Directory(source_directory=box.path("tree"))},
        ),
        dry_run=True,
    )

    printed: str = capsys.readouterr().out
    assert box.path("p/wrong") in printed
    assert box.path("p/dir/a.txt") in printed
    assert f"{box.path('p/mode')} (mode 600 -> 644)" in printed
    assert os.readlink(box.path("p/wrong")) == "/old"


def test_a_dry_run_reads_a_missing_source(box: harness.Box) -> None:
    # Reading the source shows a missing one before a real run.
    module: harness.Rec = box.rec("m", files={box.path("p/a"): engine.File(source_file=box.path("missing"))})

    with pytest.raises(engine.fs.InstallError, match="Source file doesn't exist"):
        box.apply(module, dry_run=True)
