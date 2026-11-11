"""Deploy the NosArch checkout.

From the repository root:

    python -m nosarch
    python -m nosarch --dry-run
"""

import nosarch.definition.source
import nosarch.engine.app


def main() -> None:
    nosarch.engine.app.main(nosarch.definition.source.setup)


if __name__ == "__main__":
    main()
