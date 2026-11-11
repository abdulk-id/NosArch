"""Deploy the NosArch checkout.

python -m nosarch [--dry-run]
"""

import sys
from pathlib import Path

# A real run is root. Root-owned bytecode in the checkout would not be removable by the user.
sys.dont_write_bytecode = True

# Executing this file puts its directory on the path. The package lives in the parent.
_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import nosarch.definition.source  # noqa: E402
import nosarch.engine.app  # noqa: E402

if __name__ == "__main__":
    nosarch.engine.app.main(nosarch.definition.source.setup)
