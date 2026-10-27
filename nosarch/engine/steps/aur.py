"""Installs, upgrades, and removes foreign packages: AUR packages, and custom packages built from local PKGBUILDs."""

import engine.aur
import engine.command
import engine.module
import engine.output
import engine.pacman_db
import engine.setup

# Mark a module method as returning `set[str]` of AUR package names.
packages = engine.module.declares("aur")
# Mark a module method as returning `set[str]` of custom package names. `AurSettings.custom_pkgbuild_dir` says where
# each one's PKGBUILD is.
custom_packages = engine.module.declares("custom")


def _custom_infos(ctx: engine.setup.Context, names: set[str]) -> dict[str, engine.aur.PackageInfo]:
    settings: engine.setup.AurSettings = ctx.setup.aur
    infos: dict[str, engine.aur.PackageInfo] = {}
    unavailable: list[str] = []

    for name in sorted(names):
        directory: str | None = None
        if settings.custom_pkgbuild_dir is not None:
            # A dry run only reads what is already on disk, since fetching writes to a root-owned cache.
            directory = settings.custom_pkgbuild_dir(name, not ctx.dry_run)
        if directory is None:
            unavailable.append(name)
            continue
        infos[name] = engine.aur.custom_info(name, directory, settings.build_user)

    if unavailable:
        if not ctx.dry_run:
            raise engine.aur.AurError(f"No PKGBUILD found for custom packages: {', '.join(unavailable)}.")
        engine.output.print_list("Custom packages not fetched yet, so not checked for upgrades:", unavailable)

    return infos


def _upgrades(
    ctx: engine.setup.Context,
    rpc: engine.aur.Rpc,
    custom: dict[str, engine.aur.PackageInfo],
    installed: dict[str, engine.pacman_db.LocalPackage],
    candidates: set[str],
) -> set[str]:
    try:
        rpc.fetch(candidates - set(custom))
    except engine.aur.AurError as error:
        engine.output.print_warning(f"{error} Foreign packages are not upgraded this run.")
        return set()

    upgrades: set[str] = set()
    unknown: list[str] = []

    for name in sorted(candidates):
        info: engine.aur.PackageInfo | None = custom.get(name) or rpc.get(name)
        if info is None:
            if name not in ctx.declared("custom"):
                unknown.append(name)
            continue

        devel: bool = ctx.setup.aur.upgrade_devel and engine.aur.is_devel(name)
        if devel or engine.aur.vercmp(installed[name].version, info.version) < 0:
            upgrades.add(name)

    engine.output.print_list("Foreign packages not in the AUR, so not upgraded:", unknown)
    return upgrades


def _build_and_install(
    ctx: engine.setup.Context,
    resolver: engine.aur.Resolver,
    targets: set[str],
    explicit: set[str],
    installed: dict[str, engine.pacman_db.LocalPackage],
) -> None:
    settings: engine.setup.AurSettings = ctx.setup.aur
    plan: engine.aur.Plan = resolver.resolve(targets)
    builder: engine.aur.Builder = engine.aur.Builder(settings, ctx.state)

    def build_requirements(name: str) -> set[str]:
        """Foreign packages that have to be present to build `name`."""
        required: set[str] = plan.runtime_closure(plan.build_needs[name])
        # On the host, what is installed already is there for the build. A chroot starts empty.
        return required if settings.clean_chroot else required - set(installed)

    # What ends up installed: the targets and whatever they need to run that is not installed yet.
    to_install: set[str] = targets | (plan.runtime_closure(targets) - set(installed))

    # What has to be built or taken from the cache: those, and in turn whatever their builds need.
    needed: set[str] = set(to_install)
    changed: bool = True
    while changed:
        changed = False
        for name in tuple(needed):
            if builder.cached(plan.infos[name]) is None and not build_requirements(name) <= needed:
                needed |= build_requirements(name)
                changed = True

    to_build: list[str] = [
        name for name in plan.build_order if name in needed and builder.cached(plan.infos[name]) is None
    ]

    engine.output.print_list("Foreign packages to build:", to_build)
    engine.output.print_list("Foreign dependencies to install:", to_install - targets)
    if to_build and not engine.output.prompt_confirm("Proceed?", default=True):
        raise engine.aur.AurError("Building was declined.")

    files: dict[str, str] = {}
    installed_for_build: set[str] = set()
    before: set[str] = set(installed)

    builder.prepare()
    try:
        for name in plan.build_order:
            if name not in needed or name in files:
                continue

            info: engine.aur.PackageInfo = plan.infos[name]
            cached: str | None = builder.cached(info)
            if cached is not None:
                files[name] = cached
                continue

            members: list[engine.aur.PackageInfo] = [
                plan.infos[member]
                for member in plan.build_order
                if plan.infos[member].base == info.base and member in needed and member not in files
            ]
            # Members of one package base are built together, so one never has to be installed for another.
            requirements: set[str] = {
                requirement
                for member in members
                for requirement in build_requirements(member.name)
                if plan.infos[requirement].base != info.base
            }

            if not settings.clean_chroot:
                _install_build_dependencies(members, requirements, files, installed_for_build)

            builder.build(members, [files[requirement] for requirement in sorted(requirements)])
            files.update({member.name: builder.built[member.name] for member in members})
    finally:
        builder.cleanup()

    final: list[str] = [files[name] for name in sorted(to_install) if name not in installed_for_build]
    if final:
        engine.output.print_summary("Installing foreign packages.")
        engine.command.run(["pacman", "-U", "--asdeps", *final])
    if explicit:
        engine.command.run(["pacman", "-D", "--asexplicit", *sorted(explicit)], capture=True)

    if not settings.clean_chroot:
        # What a build needed and nothing installed needs now.
        leftovers: set[str] = set(engine.command.run(["pacman", "-Qqdt"], capture=True, check=False).split())
        leftovers &= set(engine.pacman_db.local_packages()) - before
        if leftovers:
            engine.output.print_list("Removing build dependencies:", leftovers)
            engine.command.run(["pacman", "-Rns", "--noconfirm", *sorted(leftovers)])


def _install_build_dependencies(
    members: list[engine.aur.PackageInfo], requirements: set[str], files: dict[str, str], installed_for_build: set[str]
) -> None:
    """Without a chroot, a build runs on the host, so whatever it needs has to be installed there first."""

    foreign_files: list[str] = [files[name] for name in sorted(requirements)]
    if foreign_files:
        engine.command.run(["pacman", "-U", "--asdeps", "--noconfirm", *foreign_files])
        installed_for_build.update(requirements)

    dependencies: set[str] = set().union(*(set(member.build_dependencies()) for member in members))
    missing: set[str] = engine.aur.unsatisfied_on_host(dependencies)
    from_repos: set[str] = missing - engine.aur.repo_unresolvable(missing)
    if from_repos:
        engine.command.run(["pacman", "-S", "--needed", "--asdeps", "--noconfirm", *sorted(from_repos)])


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking foreign packages.")

    settings: engine.setup.AurSettings = ctx.setup.aur
    declared_custom: set[str] = ctx.declared("custom")
    declared: set[str] = ctx.declared("aur") | declared_custom

    installed: dict[str, engine.pacman_db.LocalPackage] = engine.pacman_db.local_packages()
    foreign: dict[str, engine.pacman_db.LocalPackage] = {name: pkg for name, pkg in installed.items() if not pkg.native}
    explicit_foreign: set[str] = {name for name, pkg in foreign.items() if pkg.explicit}
    explicit_native: set[str] = {name for name, pkg in installed.items() if pkg.explicit and pkg.native}
    orphans: set[str] = engine.pacman_db.orphans(installed, native=False)

    remove, demote = engine.pacman_db.split_removals(
        installed,
        (explicit_foreign | orphans) - declared - settings.ignored,
        # An ignored package's dependencies stay, since the package itself stays.
        keep=declared | explicit_native | (settings.ignored & explicit_foreign),
    )
    demote -= orphans

    to_install: set[str] = declared - set(foreign) - settings.ignored
    to_mark: set[str] = {name for name in declared & set(foreign) if not foreign[name].explicit} - settings.ignored

    rpc: engine.aur.Rpc = engine.aur.Rpc()
    custom: dict[str, engine.aur.PackageInfo] = _custom_infos(ctx, declared_custom - settings.ignored)
    upgrades: set[str] = _upgrades(ctx, rpc, custom, installed, set(foreign) - remove - settings.ignored)

    dry: bool = ctx.dry_run
    engine.output.print_list("Removing foreign packages:" if not dry else "Foreign packages to remove:", remove)
    engine.output.print_list("Marking foreign packages nothing declares as dependencies:", demote)
    engine.output.print_list("Marking declared foreign packages as explicitly installed:", to_mark)
    engine.output.print_list("Upgrading foreign packages:" if not dry else "Foreign packages to upgrade:", upgrades)
    engine.output.print_list("Installing foreign packages:" if not dry else "Foreign packages to install:", to_install)

    if dry:
        return

    if remove:
        engine.command.run(["pacman", "-Rs", *sorted(remove)])
    if demote:
        engine.command.run(["pacman", "-D", "--asdeps", *sorted(demote)], capture=True)
    if to_mark:
        engine.command.run(["pacman", "-D", "--asexplicit", *sorted(to_mark)], capture=True)

    targets: set[str] = to_install | upgrades
    if not targets:
        return

    explicit: set[str] = to_install | {name for name in upgrades if foreign[name].explicit}
    resolver: engine.aur.Resolver = engine.aur.Resolver(rpc, custom, host_satisfies=not settings.clean_chroot)
    _build_and_install(ctx, resolver, targets, explicit, installed)
