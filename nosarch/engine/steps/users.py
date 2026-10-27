"""Creates the declared accounts and keeps their groups in step."""

import grp
import pwd

import engine.command
import engine.output
import engine.setup


def _supplementary_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for entry in grp.getgrall():
        for member in entry.gr_mem:
            groups.setdefault(member, set()).add(entry.gr_name)
    return groups


def _group_exists(name: str) -> bool:
    try:
        grp.getgrnam(name)
    except KeyError:
        return False
    return True


def _create(ctx: engine.setup.Context, user: engine.setup.User) -> None:
    cmd: list[str] = ["useradd"]
    if user.group:
        cmd += ["--gid", user.group] if _group_exists(user.group) else ["--user-group"]
    if user.home:
        cmd += ["--create-home", "--home-dir", user.home]
    if user.shell:
        cmd += ["--shell", user.shell]

    groups: list[str] = [name for name in user.groups if _group_exists(name)]
    if groups:
        cmd += ["--groups", ",".join(groups)]
    if user.system:
        cmd.append("--system")
    cmd.append(user.username)

    engine.output.print_info(f"Creating user {user.username}.")
    if not ctx.dry_run:
        engine.command.run(cmd)
        ctx.state.created_users.append(user.username)


def _sync(ctx: engine.setup.Context, user: engine.setup.User, final: bool) -> None:
    entry: pwd.struct_passwd = pwd.getpwnam(user.username)
    cmd: list[str] = ["usermod"]

    if user.shell and user.shell != entry.pw_shell:
        cmd += ["--shell", user.shell]

    if user.group and _group_exists(user.group) and grp.getgrnam(user.group).gr_gid != entry.pw_gid:
        cmd += ["--gid", user.group]

    # A group a package creates, such as `libvirt`, does not exist until the package step has run. Those are added
    # when this runs again after the steps.
    wanted: set[str] = {name for name in user.groups if _group_exists(name)}
    missing: set[str] = set(user.groups) - wanted
    current: set[str] = _supplementary_groups().get(user.username, set())

    # The primary group is never listed as a member of itself, so it is left out of the comparison.
    primary: str = grp.getgrgid(entry.pw_gid).gr_name
    if wanted - {primary} != current - {primary}:
        engine.output.print_list(f"Setting groups of {user.username}:", sorted(wanted))
        cmd += ["--groups", ",".join(sorted(wanted))]

    if missing and final:
        engine.output.print_warning(f"Groups for {user.username} do not exist: {', '.join(sorted(missing))}.")

    if len(cmd) > 1:
        engine.output.print_info(f"Updating user {user.username}.")
        if not ctx.dry_run:
            engine.command.run([*cmd, user.username])


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking users.")

    declared: set[str] = {user.username for user in ctx.setup.users}

    for user in ctx.setup.users:
        try:
            pwd.getpwnam(user.username)
        except KeyError:
            _create(ctx, user)
            continue
        _sync(ctx, user, final=False)

    for username in sorted(set(ctx.state.created_users) - declared):
        engine.output.print_info(f"Deleting user {username}.")
        if not ctx.dry_run:
            engine.command.run(["userdel", username], check=False)
            ctx.state.created_users.remove(username)


def finish(ctx: engine.setup.Context) -> None:
    """Adds the groups that only came into existence during this run's package steps."""

    for user in ctx.setup.users:
        try:
            pwd.getpwnam(user.username)
        except KeyError:
            continue
        _sync(ctx, user, final=True)
