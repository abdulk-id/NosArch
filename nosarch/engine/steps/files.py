import os
import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass

import engine.command
import engine.fs
import engine.output
import engine.setup


@dataclass
class _Entry:
    module: str
    file: engine.fs.File | None = None
    variables: dict[str, str] | None = None
    symlink: engine.fs.Symlink | None = None


class DuplicateTargetError(Exception):
    pass


def _gather(ctx: engine.setup.Context) -> dict[str, _Entry]:
    entries: dict[str, _Entry] = {}

    def add(target: str, entry: _Entry) -> None:
        if target in entries:
            raise DuplicateTargetError(f"'{target}' is declared by both {entries[target].module} and {entry.module}.")
        entries[target] = entry

    for module in ctx.setup.modules:
        variables: dict[str, str] = module.file_variables()

        for target, file in module.files().items():
            add(target, _Entry(module.name, file=file, variables=variables))

        for target_directory, directory in module.directories().items():
            for target, file in directory.files(target_directory).items():
                add(target, _Entry(module.name, file=file, variables=variables))

        for target, link in module.symlinks().items():
            add(
                target,
                _Entry(module.name, symlink=link if isinstance(link, engine.fs.Symlink) else engine.fs.Symlink(link)),
            )

    return entries


def _file_differences(target: str, content: bytes, mode: int, uid: int | None, gid: int | None) -> list[str]:
    try:
        status: os.stat_result = os.lstat(target)
    except FileNotFoundError:
        return ["new"]

    if not stat.S_ISREG(status.st_mode):
        return ["replaces a non-file"]

    differences: list[str] = []
    with open(target, "rb") as current:
        if current.read() != content:
            differences.append("content")

    if stat.S_IMODE(status.st_mode) != mode:
        differences.append(f"mode {stat.S_IMODE(status.st_mode):o} -> {mode:o}")

    if (uid is not None and status.st_uid != uid) or (gid is not None and status.st_gid != gid):
        differences.append("owner")

    return differences


def _link_differences(target: str, link: engine.fs.Symlink) -> list[str]:
    if not os.path.islink(target):
        return ["new"] if not os.path.lexists(target) else ["replaces a non-link"]
    current: str = os.readlink(target)
    if current != link.target:
        return [f"was -> {current}"]
    return []


def _make_parents(directory: str, uid: int | None, gid: int | None) -> None:
    if os.path.isdir(directory):
        return

    _make_parents(os.path.dirname(directory), uid, gid)
    os.mkdir(directory, 0o755)
    if uid is not None or gid is not None:
        os.chown(directory, uid if uid is not None else -1, gid if gid is not None else -1)


def _write_file(target: str, content: bytes, mode: int, uid: int | None, gid: int | None) -> None:
    directory: str = os.path.dirname(target)
    _make_parents(directory, uid, gid)

    try:
        existing: os.stat_result | None = os.lstat(target)
    except FileNotFoundError:
        existing = None
    if existing is not None and stat.S_ISREG(existing.st_mode):
        uid = existing.st_uid if uid is None else uid
        gid = existing.st_gid if gid is None else gid

    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f".{os.path.basename(target)}.")
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            if uid is not None or gid is not None:
                os.fchown(file.fileno(), uid if uid is not None else -1, gid if gid is not None else -1)
            os.fchmod(file.fileno(), mode)
        os.replace(temporary, target)
    except BaseException:
        if os.path.lexists(temporary):
            os.unlink(temporary)
        raise


def _write_link(target: str, link: engine.fs.Symlink) -> None:
    uid, gid = link.ids()
    _make_parents(os.path.dirname(target), uid, gid)

    if os.path.lexists(target):
        os.unlink(target)
    os.symlink(link.target, target)

    if uid is not None or gid is not None:
        os.lchown(target, uid if uid is not None else -1, gid if gid is not None else -1)


def _render(file: engine.fs.File, target: str, variables: dict[str, str]) -> bytes:
    prefix: str = f"Failed to install file from {file.describe()} to {target}: "
    try:
        return file.render(variables)
    except PermissionError:
        raise
    except FileNotFoundError as error:
        raise engine.fs.InstallError(f"{prefix}Source file doesn't exist.") from error
    except UnicodeDecodeError as error:
        raise engine.fs.InstallError(f"{prefix}Unicode decoding failed.") from error
    except UnicodeEncodeError as error:
        raise engine.fs.InstallError(f"{prefix}Unicode encoding failed.") from error
    except OSError as error:
        raise engine.fs.InstallError(f"{prefix}{error.strerror or error}.") from error


def _guard(prefix: str, action: Callable[[], None]) -> None:
    try:
        action()
    except PermissionError:
        raise
    except OSError as error:
        raise engine.fs.InstallError(f"{prefix}{error.strerror or error}.") from error


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking files.")

    entries: dict[str, _Entry] = _gather(ctx)
    updated: list[str] = []
    unreadable: list[str] = []

    for target, entry in entries.items():
        try:
            if entry.symlink is not None:
                link: engine.fs.Symlink = entry.symlink
                differences: list[str] = _link_differences(target, link)
                if differences and not ctx.dry_run:
                    _guard(
                        f"Failed to install symlink from {target} to {link.target}: ", lambda: _write_link(target, link)
                    )
            else:
                assert entry.file is not None and entry.variables is not None
                file: engine.fs.File = entry.file
                content: bytes = _render(file, target, entry.variables)
                uid, gid = file.ids()
                differences = _file_differences(target, content, file.permissions, uid, gid)
                if differences and not ctx.dry_run:
                    _guard(
                        f"Failed to install file from {file.describe()} to {target}: ",
                        lambda: _write_file(target, content, file.permissions, uid, gid),
                    )
        except PermissionError:
            if not ctx.dry_run:
                raise
            unreadable.append(target)
            continue
        except engine.command.AccountNotFoundError:
            if not ctx.dry_run:
                raise
            differences = ["owner does not exist yet"]

        if differences:
            updated.append(f"{target} ({', '.join(differences)})")
            ctx.changes_for(entry.module).changed_files.add(target)

    previous_owner: dict[str, str] = {path: module for module, paths in ctx.state.files.items() for path in paths}

    removed: list[str] = []
    for path, module in sorted(previous_owner.items()):
        if path in entries:
            continue
        if not os.path.lexists(path) or (os.path.isdir(path) and not os.path.islink(path)):
            continue

        removed.append(path)
        ctx.changes_for(module).changed_files.add(path)
        if not ctx.dry_run:
            try:
                os.remove(path)
            except OSError as error:
                engine.output.print_warning(f"Could not remove '{path}': {error.strerror or error}.")

    engine.output.print_list("Updated files:", updated, one_per_line=True)
    engine.output.print_list("Removed files:", removed, one_per_line=True)
    engine.output.print_list("Files that need root to compare:", unreadable, one_per_line=True)

    if not ctx.dry_run:
        ctx.state.files = {}
        for target, entry in entries.items():
            ctx.state.files.setdefault(entry.module, []).append(target)
