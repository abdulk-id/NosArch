"""Deploys every declared file and symlink, and removes the ones no module declares any more."""

import os
import stat
import tempfile
from dataclasses import dataclass

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
    """
    How `target` differs from what is declared, or an empty list when it already matches.

    Raises PermissionError when the target cannot be read, which only a dry run without root can run into.
    """

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
    if os.readlink(target) != link.target:
        return [f"was -> {os.readlink(target)}"]
    return []


def _make_parents(directory: str, uid: int | None, gid: int | None) -> None:
    """Creates missing parent directories, owned like the file going into them."""

    if os.path.isdir(directory):
        return

    _make_parents(os.path.dirname(directory), uid, gid)
    os.mkdir(directory, 0o755)
    if uid is not None or gid is not None:
        os.chown(directory, uid if uid is not None else -1, gid if gid is not None else -1)


def _write_file(target: str, content: bytes, mode: int, uid: int | None, gid: int | None) -> None:
    """Writes through a temporary file and a rename, so a reader never sees a half-written file."""

    directory: str = os.path.dirname(target)
    _make_parents(directory, uid, gid)

    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f".{os.path.basename(target)}.")
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            os.fchmod(file.fileno(), mode)
            if uid is not None or gid is not None:
                os.fchown(file.fileno(), uid if uid is not None else -1, gid if gid is not None else -1)
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


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking files.")

    entries: dict[str, _Entry] = _gather(ctx)
    updated: list[str] = []
    unreadable: list[str] = []

    for target, entry in entries.items():
        try:
            if entry.symlink is not None:
                differences: list[str] = _link_differences(target, entry.symlink)
                if differences and not ctx.dry_run:
                    _write_link(target, entry.symlink)
            else:
                assert entry.file is not None and entry.variables is not None
                content: bytes = entry.file.render(entry.variables)
                uid, gid = entry.file.ids()
                differences = _file_differences(target, content, entry.file.permissions, uid, gid)
                if differences and not ctx.dry_run:
                    _write_file(target, content, entry.file.permissions, uid, gid)
        except PermissionError:
            if not ctx.dry_run:
                raise
            unreadable.append(target)
            continue
        except KeyError as error:
            # The owner or group of a file does not exist yet. The users step creates it on a real run.
            if not ctx.dry_run:
                raise
            differences = [f"owner {error} does not exist yet"]

        if differences:
            updated.append(f"{target} ({', '.join(differences)})")
            ctx.changes_for(entry.module).changed_files.add(target)

    # Every path deployed on the last run, by the module that deployed it.
    previous_owner: dict[str, str] = {}
    for module, paths in ctx.state.files.items():
        for path in paths:
            previous_owner[path] = module

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

    engine.output.print_list("Updated files:" if not ctx.dry_run else "Files to update:", updated, one_per_line=True)
    engine.output.print_list("Removed files:" if not ctx.dry_run else "Files to remove:", removed, one_per_line=True)
    engine.output.print_list("Files that need root to compare:", unreadable, one_per_line=True)

    if not ctx.dry_run:
        deployed: dict[str, list[str]] = {}
        for target, entry in entries.items():
            deployed.setdefault(entry.module, []).append(target)
        ctx.state.files = deployed
