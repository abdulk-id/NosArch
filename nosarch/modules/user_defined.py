import decman
from decman.plugins import aur, flatpak, pacman
from plugins import homebrew, snap
from utils.user_config_reader import UserConfigReader


class UserDefinedModule(decman.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="user_defined")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.get_str("user.username")

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def arch_pkgs(self) -> set[str]:
        return set(self._user_config.get_str_list("user_packages.arch"))

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return set(self._user_config.get_str_list("user_packages.aur"))

    @flatpak.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_pkgs(self) -> set[str]:
        if not self._user_config.get_bool("packaging.flatpak"):
            return set()

        return set(self._user_config.get_str_list("user_packages.flatpak"))

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        if not self._user_config.get_bool("packaging.flatpak"):
            return {}

        return {self._username: set(self._user_config.get_str_list("user_packages.flatpak_user"))}

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        return set(self._user_config.get_str_list("user_packages.homebrew_formulae"))

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        return set(self._user_config.get_str_list("user_packages.homebrew_casks"))

    @snap.snaps  # pyright: ignore[reportUnknownMemberType]
    def snaps(self) -> dict[str, str]:
        if not self._user_config.get_bool("packaging.snap"):
            return {}

        return self._user_config.get_str_dict("user_packages.snap")

    @snap.classic_snaps  # pyright: ignore[reportUnknownMemberType]
    def classic_snaps(self) -> dict[str, str]:
        if not self._user_config.get_bool("packaging.snap"):
            return {}

        return self._user_config.get_str_dict("user_packages.classic_snap")
