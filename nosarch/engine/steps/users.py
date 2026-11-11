import grp
import pwd

import nosarch.engine.command
import nosarch.engine.output
import nosarch.engine.setup


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


def _create(ctx: nosarch.engine.setup.Context, user: nosarch.engine.setup.User) -> None:
    cmd: list[str] = ["useradd"]
    if user.group:
        if _group_exists(user.group) or user.group != user.username:
            cmd += ["--gid", user.group]
        else:
            cmd.append("--user-group")
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

    nosarch.engine.output.print_info(f"Creating user {user.username}.")
    if not ctx.dry_run:
        nosarch.engine.command.run(cmd)
        ctx.state.created_users.append(user.username)


def _sync(ctx: nosarch.engine.setup.Context, user: nosarch.engine.setup.User, final: bool) -> None:
    entry: pwd.struct_passwd = pwd.getpwnam(user.username)
    cmd: list[str] = ["usermod"]

    if user.group and _group_exists(user.group) and grp.getgrnam(user.group).gr_gid != entry.pw_gid:
        cmd += ["--gid", user.group]

    if user.home and user.home != entry.pw_dir:
        cmd += ["--move-home", "--home", user.home]

    if user.shell and user.shell != entry.pw_shell:
        cmd += ["--shell", user.shell]

    wanted: set[str] = {name for name in user.groups if _group_exists(name)}
    missing: set[str] = set(user.groups) - wanted
    current: set[str] = _supplementary_groups().get(user.username, set())

    primary: str = grp.getgrgid(entry.pw_gid).gr_name
    if wanted - {primary} != current - {primary}:
        nosarch.engine.output.print_list(f"Setting groups of {user.username}:", sorted(wanted))
        cmd += ["--groups", ",".join(sorted(wanted))]

    if missing and final:
        nosarch.engine.output.print_warning(f"Groups for {user.username} do not exist: {', '.join(sorted(missing))}.")

    if len(cmd) > 1:
        nosarch.engine.output.print_info(f"Updating user {user.username}.")
        if not ctx.dry_run:
            nosarch.engine.command.run([*cmd, user.username])


def run(ctx: nosarch.engine.setup.Context) -> None:
    nosarch.engine.output.print_summary("Checking users.")

    declared: set[str] = {user.username for user in ctx.setup.users}

    for user in ctx.setup.users:
        try:
            pwd.getpwnam(user.username)
        except KeyError:
            _create(ctx, user)
            continue
        _sync(ctx, user, final=False)

    for username in sorted(set(ctx.state.created_users) - declared):
        nosarch.engine.output.print_info(f"Deleting user {username}.")
        if not ctx.dry_run:
            nosarch.engine.command.run(["userdel", username], check=False)
            ctx.state.created_users.remove(username)


def finish(ctx: nosarch.engine.setup.Context) -> None:
    for user in ctx.setup.users:
        try:
            pwd.getpwnam(user.username)
        except KeyError:
            continue
        _sync(ctx, user, final=True)
