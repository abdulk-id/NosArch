"""Where this checkout lives on disk.

The clone is the program. Dotfiles sit next to the package, and a run finds them from this file
rather than from the process working directory.
"""

import os


def root() -> str:
    """The directory that contains the `nosarch` package and `dotfiles/`."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
