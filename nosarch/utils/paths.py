import os

from nosarch.engine import File


def in_package(*parts: str) -> str:
    """A path inside the `nosarch` package, independent of the process working directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parts)


def _source_root(source_root: str) -> str:
    if os.path.isabs(source_root):
        return source_root
    return in_package("dotfiles", source_root)


def _dot_source_path(rel_path: str) -> str:
    segments: list[str] = rel_path.split("/")  # ["", ".bashrc"] or ["", ".config", "hypr", "hyprland.lua"]
    return "/".join("dot_" + seg[1:] if seg.startswith(".") else seg for seg in segments)


class Dotfiles:
    def __init__(self, source_root: str) -> None:
        # A relative root is a mirrored tree under `nosarch/dotfiles/`, for example `system-root`.
        self._source_root: str = _source_root(source_root)

    def files(
        self, *target_paths: str, bin_file: bool = False, owner: str = "root", permissions: int = 0o644
    ) -> dict[str, File]:
        return {
            path: File(
                source_file=f"{self._source_root}{path}", bin_file=bin_file, owner=owner, permissions=permissions
            )
            for path in target_paths
        }


class UserhomeDotfiles:
    def __init__(self, source_root: str, username: str) -> None:
        self._source_root: str = _source_root(source_root)
        self._username: str = username

    def files(self, *rel_paths: str, bin_file: bool = False, permissions: int = 0o644) -> dict[str, File]:
        return {
            f"/home/{self._username}{rel}": File(
                source_file=f"{self._source_root}/home/username{_dot_source_path(rel)}",
                bin_file=bin_file,
                permissions=permissions,
                owner=self._username,
            )
            for rel in rel_paths
        }
