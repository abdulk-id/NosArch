"""The checkout that contains this package.

A real run changes to this directory before restarting with sudo, so `python -m nosarch` can import the package.
"""

import os


def root() -> str:
    """The directory that contains the `nosarch` package."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
