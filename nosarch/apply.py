#!/usr/bin/env python3
"""Deploy the NosArch checkout. Same as `python -m nosarch` from the repository root."""

import sys
from pathlib import Path

# A real run is root. Root-owned bytecode in the checkout would not be removable by the user.
sys.dont_write_bytecode = True

# Executing this file puts `nosarch/` on the path. The package lives in the repository root.
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from nosarch.__main__ import main  # noqa: E402

main()
