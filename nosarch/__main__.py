"""Deploy the NosArch checkout.

    python -m nosarch [--dry-run]
"""

import nosarch.definition.source
import nosarch.engine.app

if __name__ == "__main__":
    nosarch.engine.app.main(nosarch.definition.source.setup)
