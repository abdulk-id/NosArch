"""
Looks up, resolves, and builds AUR and custom packages.

Packages are built by an unprivileged user and installed by root with `pacman -U`. By default every build runs in a
fresh chroot, so nothing installed on the host can leak into it. With the chroot off, makepkg runs on the host, and
whatever a build needs is installed as a dependency first and removed once nothing needs it.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

import engine.command
import engine.output
import engine.setup
import engine.state

_RPC_URL: str = "https://aur.archlinux.org/rpc/v5"
_GIT_URL: str = "https://aur.archlinux.org/{base}.git"
_RPC_TIMEOUT: int = 30
# The AUR caps a request's URL length. 150 names keep well under it.
_RPC_BATCH: int = 150

_DEVEL_SUFFIXES: tuple[str, ...] = ("-git", "-hg", "-bzr", "-svn", "-cvs", "-darcs")

_PACKAGE_FILE: re.Pattern[str] = re.compile(r"^(?P<stem>.+)\.pkg\.tar(\.[A-Za-z0-9]+)?$")

_HOST_PACMAN_CONF: str = "/etc/pacman.conf"


class AurError(Exception):
    pass


@dataclass
class PackageInfo:
    name: str
    base: str
    version: str
    depends: list[str] = field(default_factory=list)
    makedepends: list[str] = field(default_factory=list)
    checkdepends: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    # Where a custom package's PKGBUILD lives. None for an AUR package, which is cloned from the AUR.
    custom_dir: str | None = None

    def build_dependencies(self) -> list[str]:
        return self.depends + self.makedepends + self.checkdepends


def strip_version(dependency: str) -> str:
    return re.split(r"[<>=]", dependency, maxsplit=1)[0]


def is_devel(name: str) -> bool:
    return name.endswith(_DEVEL_SUFFIXES)


def vercmp(installed: str, available: str) -> int:
    """Below zero when `available` is newer than `installed`, as pacman orders versions."""
    return int(engine.command.run(["vercmp", installed, available], capture=True).strip())


# --- Package metadata ---


class Rpc:
    """The AUR's RPC interface, with every answer cached for the run."""

    def __init__(self) -> None:
        self._cache: dict[str, PackageInfo | None] = {}

    def _request(self, url: str) -> dict:
        request: urllib.request.Request = urllib.request.Request(url, headers={"User-Agent": "nosarch-engine"})
        try:
            with urllib.request.urlopen(request, timeout=_RPC_TIMEOUT) as response:
                data: dict = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise AurError(f"Could not reach the AUR: {error}") from error

        if data.get("type") == "error":
            raise AurError(f"The AUR answered with an error: {data.get('error')}")
        return data

    def fetch(self, names: set[str]) -> None:
        missing: list[str] = sorted(name for name in names if name not in self._cache)

        for start in range(0, len(missing), _RPC_BATCH):
            batch: list[str] = missing[start : start + _RPC_BATCH]
            query: str = urllib.parse.urlencode([("arg[]", name) for name in batch])
            for result in self._request(f"{_RPC_URL}/info?{query}")["results"]:
                self._cache[result["Name"]] = PackageInfo(
                    name=result["Name"],
                    base=result["PackageBase"],
                    version=result["Version"],
                    depends=result.get("Depends", []),
                    makedepends=result.get("MakeDepends", []),
                    checkdepends=result.get("CheckDepends", []),
                    provides=result.get("Provides", []),
                )
            for name in batch:
                self._cache.setdefault(name, None)

    def get(self, name: str) -> PackageInfo | None:
        self.fetch({name})
        return self._cache[name]

    def providers(self, name: str) -> list[str]:
        data: dict = self._request(f"{_RPC_URL}/search/{urllib.parse.quote(name)}?by=provides")
        return sorted(result["Name"] for result in data["results"])


def parse_srcinfo(srcinfo: str, pkgname: str, custom_dir: str) -> PackageInfo:
    """Reads one package out of `makepkg --printsrcinfo`, including split packages and arch-specific fields."""

    arch: str = os.uname().machine
    base: str | None = None
    values: dict[str, str] = {}
    lists: dict[str, list[str]] = {"depends": [], "makedepends": [], "checkdepends": [], "provides": []}
    current: str | None = None
    found: bool = False

    for raw in srcinfo.splitlines():
        line: str = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = (part.strip() for part in line.split("=", 1))

        if key == "pkgbase":
            base, current = value, None
            continue
        if key == "pkgname":
            current = value
            found = found or value == pkgname
            continue

        # Base fields apply to every package, a package's own fields override them.
        if current is not None and current != pkgname:
            continue

        if key in ("pkgver", "pkgrel", "epoch"):
            values[key] = value
            continue

        for list_key in lists:
            if key == list_key or key == f"{list_key}_{arch}":
                lists[list_key].append(value)

    if base is None or "pkgver" not in values or not found:
        raise AurError(f"Could not read package '{pkgname}' from its PKGBUILD in {custom_dir}.")

    version: str = values["pkgver"]
    if "pkgrel" in values:
        version = f"{version}-{values['pkgrel']}"
    if "epoch" in values:
        version = f"{values['epoch']}:{version}"

    return PackageInfo(name=pkgname, base=base, version=version, custom_dir=custom_dir, **lists)


def custom_info(pkgname: str, directory: str, build_user: str) -> PackageInfo:
    """Metadata of a custom package. makepkg refuses root, so root asks the build user."""

    user: str | None = build_user if engine.command.is_root() else None

    # makepkg insists its build directories are writable even when it only prints metadata, and the PKGBUILD cache is
    # root-owned. A scratch directory satisfies it.
    scratch: str = tempfile.mkdtemp(prefix="nosarch-srcinfo-")
    try:
        if user is not None:
            shutil.chown(scratch, user=user)
        locations: dict[str, str] = {key: scratch for key in ("BUILDDIR", "PKGDEST", "SRCDEST", "LOGDEST")}
        srcinfo: str = engine.command.run(
            ["makepkg", "--printsrcinfo"], user=user, cwd=directory, env=locations, capture=True
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return parse_srcinfo(srcinfo, pkgname, directory)


# --- Dependency resolution ---


def repo_unresolvable(dependencies: set[str]) -> set[str]:
    """
    The dependencies no sync repository can satisfy, by name or by what a package provides.

    pacman resolves this itself, version constraints and all, and reports each target it cannot find.
    """

    if not dependencies:
        return set()

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["pacman", "-Sp", "--noconfirm", "--print-format", "%n", "--", *sorted(dependencies)],
        env=dict(os.environ) | {"LC_ALL": "C"},
        capture_output=True,
        text=True,
        check=False,
    )

    missing: set[str] = set()
    for line in completed.stderr.splitlines():
        marker: str = "target not found: "
        if marker in line:
            missing.add(line.split(marker, 1)[1].strip())

    if completed.returncode != 0 and not missing:
        raise AurError(f"pacman could not resolve dependencies: {completed.stderr.strip()}")

    return missing


def unsatisfied_on_host(dependencies: set[str]) -> set[str]:
    """The dependencies no installed package satisfies, which `pacman -T` prints."""

    if not dependencies:
        return set()

    # pacman exits 127 when anything is unsatisfied, which is the expected answer here rather than a failure.
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["pacman", "-T", "--", *sorted(dependencies)], capture_output=True, text=True, check=False
    )
    if completed.returncode not in (0, 127):
        raise AurError(f"pacman could not check dependencies: {completed.stderr.strip()}")
    return set(completed.stdout.split())


@dataclass
class Plan:
    infos: dict[str, PackageInfo] = field(default_factory=dict)
    # Every package found, dependencies before what needs them, members of one package base next to each other.
    build_order: list[str] = field(default_factory=list)
    # For each package, the foreign packages its build needs installed: runtime, make, and check dependencies.
    build_needs: dict[str, set[str]] = field(default_factory=dict)
    # For each package, the foreign packages it needs installed to run.
    runtime_needs: dict[str, set[str]] = field(default_factory=dict)

    def runtime_closure(self, names: set[str]) -> set[str]:
        """`names` and everything they need to run, transitively."""

        closure: set[str] = set()
        stack: list[str] = sorted(names)
        while stack:
            name: str = stack.pop()
            if name in closure:
                continue
            closure.add(name)
            stack.extend(self.runtime_needs.get(name, set()))
        return closure


class Resolver:
    def __init__(self, rpc: Rpc, custom: dict[str, PackageInfo], host_satisfies: bool) -> None:
        """
        `host_satisfies` takes what is installed on the host as satisfying a dependency, which is true when builds
        run on the host. A chroot starts empty, so there every foreign dependency has to be found and built.
        """

        self._rpc: Rpc = rpc
        self._custom: dict[str, PackageInfo] = custom
        self._host_satisfies: bool = host_satisfies
        self._chosen: dict[str, str] = {}

    def info(self, name: str) -> PackageInfo:
        if name in self._custom:
            return self._custom[name]
        info: PackageInfo | None = self._rpc.get(name)
        if info is None:
            raise AurError(f"'{name}' is neither in the AUR nor a custom package.")
        return info

    def _foreign_provider(self, dependency: str) -> str:
        """The foreign package that satisfies `dependency`, asking the user when several do."""

        name: str = strip_version(dependency)
        if name in self._chosen:
            return self._chosen[name]

        for custom in self._custom.values():
            if name == custom.name or name in map(strip_version, custom.provides):
                self._chosen[name] = custom.name
                return custom.name

        if self._rpc.get(name) is not None:
            self._chosen[name] = name
            return name

        providers: list[str] = self._rpc.providers(name)
        if not providers:
            raise AurError(f"Nothing in the repositories or the AUR provides '{dependency}'.")

        choice: str = (
            providers[0]
            if len(providers) == 1
            else engine.output.prompt_choice(f"Several AUR packages provide {name}:", providers)
        )
        self._chosen[name] = choice
        return choice

    def resolve(self, targets: set[str]) -> Plan:
        """Finds every foreign package the targets need, at runtime or to build, and orders the builds."""

        plan: Plan = Plan()
        infos: dict[str, PackageInfo] = plan.infos
        queue: list[str] = sorted(targets)

        while queue:
            name: str = queue.pop()
            if name in infos:
                continue
            info: PackageInfo = self.info(name)
            infos[name] = info

            self._rpc.fetch({strip_version(dependency) for dependency in info.build_dependencies()})
            foreign: set[str] = repo_unresolvable(set(info.build_dependencies()))
            if self._host_satisfies:
                foreign &= unsatisfied_on_host(foreign)

            plan.build_needs[name] = set()
            plan.runtime_needs[name] = set()
            for dependency in info.build_dependencies():
                if dependency not in foreign:
                    continue
                provider: str = self._foreign_provider(dependency)
                if provider == name:
                    continue
                plan.build_needs[name].add(provider)
                if dependency in info.depends:
                    plan.runtime_needs[name].add(provider)
                queue.append(provider)

        # Depth-first order by package base, so a split package is built once and before what needs it.
        visiting: set[str] = set()
        done: set[str] = set()

        def visit(name: str) -> None:
            base: str = infos[name].base
            if base in done:
                return
            if base in visiting:
                raise AurError(f"Foreign packages depend on each other in a cycle through '{name}'.")
            visiting.add(base)
            for member in [info for info in infos.values() if info.base == base]:
                for dependency in plan.build_needs[member.name]:
                    if infos[dependency].base != base:
                        visit(dependency)
            visiting.discard(base)
            done.add(base)
            plan.build_order.extend(info.name for info in infos.values() if info.base == base)

        for name in sorted(infos):
            visit(name)

        return plan


# --- Package files ---


def _parse_package_file(filename: str) -> tuple[str, str] | None:
    """The package name and version of a built package file, or None for anything else."""

    match: re.Match[str] | None = _PACKAGE_FILE.match(filename)
    if match is None:
        return None

    parts: list[str] = match.group("stem").rsplit("-", 3)
    if len(parts) != 4:
        return None

    name, pkgver, pkgrel, _ = parts
    return name, f"{pkgver}-{pkgrel}"


def _package_files(directory: str) -> dict[str, tuple[str, str]]:
    """Package name to (version, path) for every package file in `directory`, keeping the newest file per name."""

    found: dict[str, tuple[str, str]] = {}
    if not os.path.isdir(directory):
        return found

    for entry in sorted(os.scandir(directory), key=lambda entry: entry.stat().st_mtime):
        if not entry.is_file() or entry.name.endswith(".sig"):
            continue
        parsed: tuple[str, str] | None = _parse_package_file(entry.name)
        if parsed is not None:
            found[parsed[0]] = (parsed[1], entry.path)

    return found


# --- Building ---


class Builder:
    def __init__(self, settings: engine.setup.AurSettings, state: engine.state.State) -> None:
        self._settings: engine.setup.AurSettings = settings
        self._state: engine.state.State = state
        self._chroot_ready: bool = False
        self.built: dict[str, str] = {}

    @property
    def _chroot_dir(self) -> str:
        return os.path.join(self._settings.build_dir, "chroot")

    def cached(self, info: PackageInfo) -> str | None:
        """A package file built earlier at the version the AUR has now. VCS packages are never taken from cache."""

        if is_devel(info.name):
            return None
        entry: tuple[str, str] | None = _package_files(self._settings.package_cache_dir).get(info.name)
        if entry is not None and entry[0] == info.version:
            return entry[1]
        return None

    def prepare(self) -> None:
        if os.path.exists(self._settings.build_dir):
            shutil.rmtree(self._settings.build_dir)
        os.makedirs(self._settings.build_dir, mode=0o755)
        os.makedirs(self._settings.package_cache_dir, mode=0o755, exist_ok=True)

    def cleanup(self) -> None:
        shutil.rmtree(self._settings.build_dir, ignore_errors=True)

    def _fetch(self, info: PackageInfo, directory: str) -> None:
        if info.custom_dir is not None:
            shutil.copytree(info.custom_dir, directory)
            return

        engine.command.run(["git", "clone", "--quiet", _GIT_URL.format(base=info.base), directory])
        self._review(info.base, directory)

    def _review(self, base: str, directory: str) -> None:
        """
        Offers the PKGBUILD for review before anything in it runs: the diff since the last reviewed commit, or every
        file the first time.
        """

        head: str = engine.command.run(["git", "-C", directory, "rev-parse", "HEAD"], capture=True).strip()
        reviewed: str | None = self._state.aur_reviewed.get(base)

        if reviewed == head:
            return

        if engine.output.prompt_confirm(f"Review the PKGBUILD of {base}?", default=True):
            history: str = engine.command.run(["git", "-C", directory, "log", "--format=%H"], capture=True)
            if reviewed is not None and reviewed in history.split():
                engine.command.run(["git", "-C", directory, "diff", reviewed, head], check=False)
            else:
                files: list[str] = sorted(
                    entry.path for entry in os.scandir(directory) if entry.is_file() and not entry.name.startswith(".")
                )
                pager: str = "less" if shutil.which("less") else "cat"
                engine.command.run([pager, *files], check=False)

        if not engine.output.prompt_confirm(f"Build {base}?", default=True):
            raise AurError(f"Building {base} was declined.")

        self._state.aur_reviewed[base] = head

    def _ensure_chroot(self) -> None:
        if self._chroot_ready:
            return

        engine.output.print_info("Creating a clean chroot to build in.")
        os.makedirs(self._chroot_dir, mode=0o755, exist_ok=True)

        # mkarchroot installs into an empty root with the host's pacman config, so the host's own hooks in
        # /etc/pacman.d/hooks run against that empty root. A hook with `Depends =` can never be satisfied there, and
        # one with `AbortOnFail` takes the build down. Package-provided hooks in /usr/share/libalpm/hooks are what the
        # chroot actually needs, and pacman always reads those.
        empty_hooks: str = os.path.join(self._settings.build_dir, "empty-hooks")
        os.makedirs(empty_hooks, exist_ok=True)
        conf: str = os.path.join(self._settings.build_dir, "chroot-pacman.conf")

        lines: list[str] = []
        with open(_HOST_PACMAN_CONF, "r", encoding="utf-8") as host_conf:
            for line in host_conf:
                if line.strip().startswith("HookDir"):
                    continue
                lines.append(line)
                if line.strip() == "[options]":
                    lines.append(f"HookDir = {empty_hooks}/\n")
        with open(conf, "w", encoding="utf-8") as chroot_conf:
            chroot_conf.writelines(lines)

        # mkarchroot sets up its own keyring. A GNUPGHOME from the caller points it at the wrong one.
        environment: dict[str, str] = {key: value for key, value in os.environ.items() if key != "GNUPGHOME"}
        engine.command.run(
            ["mkarchroot", "-C", conf, os.path.join(self._chroot_dir, "root"), "base-devel"],
            env=environment,
            pass_environment=False,
        )
        self._chroot_ready = True

    def build(self, infos: list[PackageInfo], needed_files: list[str]) -> None:
        """
        Builds one package base, and records the file of each package in `infos`.

        `needed_files` are package files of foreign dependencies, installed into the chroot before the build. A build
        without the chroot gets its dependencies installed on the host by the caller instead.
        """

        base: str = infos[0].base
        directory: str = os.path.join(self._settings.build_dir, base)
        self._fetch(infos[0], directory)
        engine.command.run(["chown", "--recursive", self._settings.build_user, directory])

        engine.output.print_summary(f"Building {base}.")
        environment: dict[str, str] = {"PKGDEST": directory}

        if self._settings.clean_chroot:
            self._ensure_chroot()
            cmd: list[str] = ["makechrootpkg", "-c", "-r", self._chroot_dir, "-U", self._settings.build_user]
            for file in needed_files:
                cmd += ["-I", file]
            engine.command.run(cmd, cwd=directory, env=environment)
        else:
            engine.command.run(
                ["makepkg", "--noconfirm", "--cleanbuild"],
                user=self._settings.build_user,
                cwd=directory,
                env=environment,
            )

        products: dict[str, tuple[str, str]] = _package_files(directory)
        for info in infos:
            if info.name not in products:
                raise AurError(f"Building {base} did not produce a package file for {info.name}.")

            _, path = products[info.name]
            destination: str = os.path.join(self._settings.package_cache_dir, os.path.basename(path))
            shutil.copy(path, destination)
            self._prune_cache(info.name, destination)
            self.built[info.name] = destination

    def _prune_cache(self, name: str, keep: str) -> None:
        for entry in os.scandir(self._settings.package_cache_dir):
            parsed: tuple[str, str] | None = _parse_package_file(entry.name.removesuffix(".sig"))
            if parsed is not None and parsed[0] == name and entry.path != keep and entry.path != f"{keep}.sig":
                os.remove(entry.path)
