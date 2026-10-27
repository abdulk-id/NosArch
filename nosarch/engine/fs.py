"""Declarations of the files, directories, and symlinks a module deploys."""

import grp
import os
import pwd


def _ids(owner: str | None, group: str | None) -> tuple[int | None, int | None]:
    """
    Resolves names to ids when the files step runs, not when a module declares them.

    A module declares its files before the users step has created the accounts they belong to, so on a first run the
    owner does not exist yet at declaration time.
    """

    uid: int | None = None
    gid: int | None = None

    if owner is not None:
        entry: pwd.struct_passwd = pwd.getpwnam(owner)
        uid, gid = entry.pw_uid, entry.pw_gid

    if group is not None:
        gid = grp.getgrnam(group).gr_gid

    return uid, gid


class File:
    """
    A file deployed from `source_file` or from `content`, exactly one of the two.

    Text files have every key of the module's `file_variables()` replaced with its value. `bin_file` copies bytes
    verbatim instead.
    """

    def __init__(
        self,
        source_file: str | None = None,
        content: str | None = None,
        bin_file: bool = False,
        encoding: str = "utf-8",
        owner: str | None = None,
        group: str | None = None,
        permissions: int = 0o644,
    ) -> None:
        if (source_file is None) == (content is None):
            raise ValueError("A File needs exactly one of source_file or content.")

        self.source_file: str | None = source_file
        self.content: str | None = content
        self.bin_file: bool = bin_file
        self.encoding: str = encoding
        self.owner: str | None = owner
        self.group: str | None = group
        self.permissions: int = permissions

    def ids(self) -> tuple[int | None, int | None]:
        return _ids(self.owner, self.group)

    def render(self, variables: dict[str, str]) -> bytes:
        """The exact bytes this file should hold on the target system."""

        # Without variables there is nothing to substitute, so even a text file is copied byte for byte. A module with
        # no variables, such as the theme's, can deploy images without marking them binary.
        if self.bin_file or not variables:
            if self.source_file is not None:
                with open(self.source_file, "rb") as source:
                    return source.read()
            assert self.content is not None
            return self.content.encode(self.encoding)

        if self.source_file is not None:
            with open(self.source_file, "r", encoding=self.encoding) as source:
                text: str = source.read()
        else:
            assert self.content is not None
            text = self.content

        for key, value in variables.items():
            text = text.replace(key, value)

        return text.encode(self.encoding)

    def describe(self) -> str:
        return self.source_file or "generated content"


class Directory:
    """
    Every file under `source_directory`, deployed with the same settings.

    NosArch declares files one by one. This exists for trees whose contents are not known in advance, such as a
    theme's wallpapers.
    """

    def __init__(
        self,
        source_directory: str,
        bin_files: bool = False,
        encoding: str = "utf-8",
        owner: str | None = None,
        group: str | None = None,
        permissions: int = 0o644,
    ) -> None:
        self.source_directory: str = source_directory
        self.bin_files: bool = bin_files
        self.encoding: str = encoding
        self.owner: str | None = owner
        self.group: str | None = group
        self.permissions: int = permissions

    def files(self, target_directory: str) -> dict[str, File]:
        files: dict[str, File] = {}

        for root, _, names in os.walk(self.source_directory):
            for name in names:
                source: str = os.path.join(root, name)
                relative: str = os.path.relpath(source, self.source_directory)
                files[os.path.normpath(os.path.join(target_directory, relative))] = File(
                    source_file=source,
                    bin_file=self.bin_files,
                    encoding=self.encoding,
                    owner=self.owner,
                    group=self.group,
                    permissions=self.permissions,
                )

        return files


class Symlink:
    """A symlink pointing at `target`. The target does not have to exist."""

    def __init__(self, target: str, owner: str | None = None, group: str | None = None) -> None:
        self.target: str = target
        self.owner: str | None = owner
        self.group: str | None = group

    def ids(self) -> tuple[int | None, int | None]:
        return _ids(self.owner, self.group)
