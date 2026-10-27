"""The engine's run order, file deployment, and change tracking, exercised without root in a scratch directory."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import override

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "nosarch"))

import engine  # noqa: E402
import engine.app  # noqa: E402
import engine.state  # noqa: E402


def _args(dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=dry_run, only=["files"], skip=[], no_hooks=False, aur_upgrade_devel=False, import_decman=False
    )


class _Module(engine.Module):
    def __init__(self, name: str, root: str, files: dict[str, str], log: list[str]) -> None:
        super().__init__(name)
        self._root: str = root
        self._files: dict[str, str] = files
        self._log: list[str] = log
        self.seen: list[engine.Changes] = []

    @override
    def files(self) -> dict[str, engine.File]:
        return {f"{self._root}/{path}": engine.File(content=content) for path, content in self._files.items()}

    @override
    def symlinks(self) -> dict[str, str | engine.Symlink]:
        return {f"{self._root}/link": "/nowhere"} if self.name == "a" else {}

    @override
    def file_variables(self) -> dict[str, str]:
        return {"%NAME%": self.name}

    @override
    def before_update(self) -> None:
        self._log.append(f"before:{self.name}")

    @override
    def on_enable(self) -> None:
        self._log.append(f"enable:{self.name}")

    @override
    def on_change(self, changes: engine.Changes) -> None:
        self._log.append(f"change:{self.name}")
        self.seen.append(changes)

    @override
    def after_update(self) -> None:
        self._log.append(f"after:{self.name}")

    @override
    def on_disable(self) -> None:
        self._log.append(f"disable:{self.name}")


class EngineTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self._scratch: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: str = self._scratch.name
        self._state_file: str = engine.state.STATE_FILE
        self._decman_store: str = engine.state.DECMAN_STORE
        engine.state.STATE_FILE = os.path.join(self.root, "state", "state.json")
        engine.state.DECMAN_STORE = os.path.join(self.root, "no-decman")
        self.log: list[str] = []

    @override
    def tearDown(self) -> None:
        engine.state.STATE_FILE = self._state_file
        engine.state.DECMAN_STORE = self._decman_store
        self._scratch.cleanup()

    def _setup(self, *modules: _Module, disabled: tuple[_Module, ...] = ()) -> engine.Setup:
        setup: engine.Setup = engine.Setup(steps=["files"])
        for module in modules:
            setup.add(module)
        for module in disabled:
            setup.add(module, enabled=False)
        return setup

    def _module(self, name: str, files: dict[str, str]) -> _Module:
        return _Module(name, self.root, files, self.log)

    def test_first_run_deploys_and_reports_everything(self) -> None:
        a: _Module = self._module("a", {"etc/a.conf": "name=%NAME%\n"})
        engine.app.run(self._setup(a), _args())

        self.assertEqual(Path(self.root, "etc/a.conf").read_text(), "name=a\n")
        self.assertEqual(os.readlink(os.path.join(self.root, "link")), "/nowhere")
        self.assertEqual(self.log, ["before:a", "enable:a", "change:a", "after:a"])
        self.assertTrue(a.seen[0].files_changed_in_dirs(f"{self.root}/etc"))
        self.assertTrue(a.seen[0].files_changed(f"{self.root}/link"))

    def test_unchanged_run_runs_no_on_change(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args())
        self.log.clear()

        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args())
        self.assertEqual(self.log, ["before:a", "after:a"])

    def test_dry_run_changes_nothing(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args(dry_run=True))

        self.assertFalse(os.path.exists(os.path.join(self.root, "a.conf")))
        self.assertFalse(os.path.exists(engine.state.STATE_FILE))
        self.assertEqual(self.log, [])

    def test_undeclared_file_is_removed_and_reported_to_its_module(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x", "old.conf": "y"})), _args())

        a: _Module = self._module("a", {"a.conf": "x"})
        engine.app.run(self._setup(a), _args())

        self.assertFalse(os.path.exists(os.path.join(self.root, "old.conf")))
        self.assertEqual(a.seen[0].changed_files, {f"{self.root}/old.conf"})

    def test_mode_drift_is_a_change(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args())
        os.chmod(os.path.join(self.root, "a.conf"), 0o600)

        a: _Module = self._module("a", {"a.conf": "x"})
        engine.app.run(self._setup(a), _args())

        self.assertEqual(os.stat(os.path.join(self.root, "a.conf")).st_mode & 0o777, 0o644)
        self.assertTrue(a.seen[0].files_changed(f"{self.root}/a.conf"))

    def test_changes_survive_a_run_that_stops_before_the_hooks(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args())

        class _Failing(_Module):
            @override
            def on_change(self, changes: engine.Changes) -> None:
                raise RuntimeError("stopped")

        failing: _Failing = _Failing("a", self.root, {"a.conf": "y"}, self.log)
        with self.assertRaises(RuntimeError):
            engine.app.run(self._setup(failing), _args())

        # The file is already in place now, so only the saved change can tell the hook about it.
        a: _Module = self._module("a", {"a.conf": "y"})
        engine.app.run(self._setup(a), _args())
        self.assertTrue(a.seen[0].files_changed(f"{self.root}/a.conf"))

    def test_disabled_module_runs_on_disable_and_loses_its_files(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"}), self._module("b", {"b.conf": "x"})), _args())
        self.log.clear()

        engine.app.run(
            self._setup(self._module("a", {"a.conf": "x"}), disabled=(self._module("b", {"b.conf": "x"}),)), _args()
        )

        self.assertIn("disable:b", self.log)
        self.assertLess(self.log.index("disable:b"), self.log.index("after:a"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "b.conf")))
        self.assertNotIn("b", engine.state.load().enabled_modules)  # pyright: ignore[reportOptionalMemberAccess]

    def test_two_modules_cannot_declare_one_path(self) -> None:
        setup: engine.Setup = self._setup(self._module("a", {"same": "x"}), self._module("b", {"same": "y"}))
        with self.assertRaises(Exception):
            engine.app.run(setup, _args())

    def test_state_is_world_readable(self) -> None:
        engine.app.run(self._setup(self._module("a", {"a.conf": "x"})), _args())
        self.assertEqual(os.stat(engine.state.STATE_FILE).st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
