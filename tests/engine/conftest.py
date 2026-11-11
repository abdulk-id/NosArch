"""Fixtures: `box` is the scratch machine, `accounts` a fake account database on top of it."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import harness
import pytest

import nosarch.engine.command
import nosarch.engine.state


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.geteuid() == 0:
        return
    skip: pytest.MarkDecorator = pytest.mark.skip(reason="needs fake root: run `mise run test-engine-root`")
    for item in items:
        if "needs_root" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def box(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[harness.Box]:
    log: list[str] = []
    commands: harness.Commands = harness.Commands(log)
    monkeypatch.setattr(nosarch.engine.command, "run", commands)
    monkeypatch.setattr(nosarch.engine.state, "STATE_FILE", str(tmp_path / "var" / "state.json"))

    root: Path = tmp_path / "machine"
    root.mkdir()
    yield harness.Box(root, log, commands)

    # A fake-root run chowns files to ids the real user cannot delete, so it has to clean up as the root it pretends to be.
    if os.geteuid() == 0:
        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def accounts(box: harness.Box, monkeypatch: pytest.MonkeyPatch) -> harness.Accounts:
    return harness.Accounts(monkeypatch, box.commands)
