import os
import pwd
import shlex
import shutil
import subprocess

import engine.output


class CommandFailedError(Exception):
    def __init__(self, cmd: list[str], code: int, output: str | None) -> None:
        super().__init__(f"Command '{shlex.join(cmd)}' returned with a non-zero exit code {code}.")
        self.cmd: list[str] = cmd
        self.code: int = code
        self.output: str | None = output


class AccountNotFoundError(LookupError):
    pass


def is_root() -> bool:
    return os.geteuid() == 0


def passwd_entry(user: str) -> pwd.struct_passwd:
    try:
        return pwd.getpwnam(user)
    except KeyError as error:
        raise AccountNotFoundError(f"The user '{user}' doesn't exist.") from error


def can_run_as(user: str) -> bool:
    return is_root() or passwd_entry(user).pw_uid == os.geteuid()


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
    environment: dict[str, str] = dict(os.environ) if pass_environment else {}
    uid: int | None = None
    gid: int | None = None
    groups: list[int] | None = None

    if user is not None:
        entry: pwd.struct_passwd = passwd_entry(user)
        environment |= {"HOME": entry.pw_dir, "USER": entry.pw_name, "LOGNAME": entry.pw_name, "SHELL": entry.pw_shell}

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

        engine.output.print_warning(f"Command '{shlex.join(cmd)}' returned with an exit code {completed.returncode}.")

    return completed.stdout if capture and completed.stdout is not None else ""


def sh(script: str, *, user: str | None = None, check: bool = True) -> str:
    return run(["/bin/sh", "-c", script], user=user, check=check)


def succeeds(cmd: list[str], *, user: str | None = None) -> bool:
    try:
        run(cmd, user=user, capture=True)
    except CommandFailedError:
        return False
    return True
