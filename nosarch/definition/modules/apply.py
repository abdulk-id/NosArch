from typing import override

import nosarch.engine
import nosarch.utils.apply


class ApplyModule(nosarch.engine.Module):
    """Runs the commands other modules requested during `on_change`.

    Registered last, in its own statement. `after_update` therefore runs after every other
    module's `after_update`, and after every `on_change` has recorded its requests.
    """

    def __init__(self) -> None:
        super().__init__(name="apply")

    @override
    def after_update(self) -> None:
        nosarch.utils.apply.flush()
