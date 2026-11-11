"""NosArch: the deployment engine and the definition of the system it deploys."""

import sys

# A real run is root. Bytecode written then would be root-owned files in the checkout.
sys.dont_write_bytecode = True
