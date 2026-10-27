"""Running commands, as root or as another user."""

import os
import pwd
import shlex
import shutil
import subprocess

import engine.output


class CommandFailedError(Exception):
    def __init__(self, cmd: list[str], code: int, output: str | None) -> None:
        super().__init__(f"Command '{shlex.join(cmd)}' exited with code {code}.")
        self.cmd: list[str] = cmd
        self.code: int = code
        self.output: str | None = output


def is_root() -> bool:
    return os.geteuid() == 0


def can_run_as(user: str) -> bool:
    """Whether `run(..., user=user)` can work: as root, or as that user."""
    return is_root() or pwd.getpwnam(user).pw_uid == os.geteuid()


def login_environment(user: str) -> dict[str, str]:
    """The variables a login as `user` would set, so programs find their own home and config."""

    entry: pwd.struct_passwd = pwd.getpwnam(user)
    return {"HOME": entry.pw_dir, "USER": entry.pw_name, "LOGNAME": entry.pw_name, "SHELL": entry.pw_shell}


def run(
    cmd: list[str],
    *,
    user: str | None = None,
    env: dict[str, str] | None = None,
    pass_environment: bool = True,
    capture: bool = False,
    check: bool = True,
    cwd: str | None = None,
) -> str:
    """
    Runs `cmd` and returns its standard output when `capture` is set, otherwise an empty string.

    Without `capture`, the command shares this terminal, so interactive programs such as pacman can prompt.

    `user` runs the command as that user, with a login environment. Root can run as anyone. Anyone else can only
    run as themselves, which is what a dry run does, so the same call works in both.

    `check` raises `CommandFailedError` on a non-zero exit. Without it a failure is only reported.
    """

    environment: dict[str, str] = dict(os.environ) if pass_environment else {}
    uid: int | None = None
    gid: int | None = None
    groups: list[int] | None = None

    if user is not None:
        environment |= login_environment(user)
        entry: pwd.struct_passwd = pwd.getpwnam(user)
        if entry.pw_uid != os.geteuid():
            if not is_root():
                raise PermissionError(f"Running '{shlex.join(cmd)}' as {user} needs root.")
            uid, gid = entry.pw_uid, entry.pw_gid
            groups = os.getgrouplist(user, entry.pw_gid)

    if env:
        environment |= env

    executable: str = shutil.which(cmd[0], path=environment.get("PATH")) or cmd[0]
    engine.output.print_debug(f"Running '{shlex.join(cmd)}'{f' as {user}' if user else ''}.")

    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            [executable, *cmd[1:]],
            env=environment,
            cwd=cwd,
            user=uid,
            group=gid,
            extra_groups=groups,
            stdout=subprocess.PIPE if capture else None,
            text=True,
            errors="replace",
            check=False,
        )
    except OSError as error:
        if check:
            raise CommandFailedError(cmd, 127, error.strerror or str(error)) from error
        engine.output.print_warning(f"Could not run '{shlex.join(cmd)}': {error.strerror or error}")
        return ""

    if completed.returncode != 0:
        if check:
            raise CommandFailedError(cmd, completed.returncode, completed.stdout if capture else None)
        engine.output.print_warning(f"Command '{shlex.join(cmd)}' exited with code {completed.returncode}.")

    return completed.stdout if capture and completed.stdout is not None else ""


def sh(script: str, *, user: str | None = None, check: bool = True) -> str:
    """Runs a shell script, see `run`."""
    return run(["/bin/sh", "-c", script], user=user, check=check)


def succeeds(cmd: list[str], *, user: str | None = None) -> bool:
    """Whether `cmd` exits zero. Its output is discarded."""

    try:
        run([*cmd], user=user, capture=True, check=True)
    except CommandFailedError:
        return False
    return True
