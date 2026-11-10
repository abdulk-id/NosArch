import grp
import os
import pwd

import engine.command


class InstallError(Exception):
    pass


def _ids(owner: str | None, group: str | None) -> tuple[int | None, int | None]:
    uid: int | None = None
    gid: int | None = None

    if owner is not None:
        entry: pwd.struct_passwd = engine.command.passwd_entry(owner)
        uid, gid = entry.pw_uid, entry.pw_gid

    if group is not None:
        try:
            gid = grp.getgrnam(group).gr_gid
        except KeyError as error:
            raise engine.command.AccountNotFoundError(f"The group '{group}' doesn't exist.") from error

    return uid, gid


class File:
    """A file from exactly one of source_file or content."""

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
    """Every file under source_directory, deployed with the same settings."""

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
        if not os.path.isdir(self.source_directory):
            raise InstallError(
                f"Failed to install file from {self.source_directory} to {target_directory}: "
                "Source directory doesn't exist."
            )

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
    """A symlink pointing at target. The target does not have to exist."""

    def __init__(self, target: str, owner: str | None = None, group: str | None = None) -> None:
        self.target: str = target
        self.owner: str | None = owner
        self.group: str | None = group

    def ids(self) -> tuple[int | None, int | None]:
        return _ids(self.owner, self.group)
