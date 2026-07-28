import decman
from decman.plugins import pacman


# Creative Setup module
class CreativeModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="creative_profile")

    @pacman.packages
    def pkgs(self) -> set[str]:
        return {"obs-studio"}
