#!/usr/bin/env python3
"""Deploys the NosArch configuration. A dry run needs no root, a real run asks for it with sudo. See `--help`."""

import os
import sys

# Run as root, Python would leave root-owned bytecode caches in the repository.
sys.dont_write_bytecode = True

# Definition code refers to dotfiles relative to this directory. `nosarch/` is on the path so `engine` and
# `definition` import by package name.
_HERE: str = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import definition.source  # noqa: E402
import engine.app  # noqa: E402

engine.app.main(definition.source.setup)
