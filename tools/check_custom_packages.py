"""
Checks the PKGBUILDs under `nosarch/packages/`.

Two independent checks:

- Freshness: compares each `pkgver` against upstream, for packages that
  declare where upstream lives (see `# nosarch-upstream:` below).
- Correctness: structural validation of the PKGBUILD itself, plus `namcap`
  if it is installed. `namcap` is the tool that reports missing and
  redundant `depends`, but it can only do that against a *built* package,
  so that part runs only with `--build`.

Declaring an upstream is opt-in. Add one directive to the PKGBUILD:

    # nosarch-upstream: json <url> <dotted.key>
    # nosarch-upstream: github <owner>/<repo>
    # nosarch-upstream: regex <url> <pattern with one capture group>

Without it, the package is only validated, never version-checked.

Usage: python3 tools/check_custom_packages.py [OPTIONS]

Options:
    -h, --help       Show this message.
    -p, --package    Check only the named package. May be repeated.
    -o, --offline    Skip upstream version checks.
    -b, --build      Build each package so namcap can audit `depends`. Slow.
    -q, --quiet      Only print packages that have something to report.

Exit status separates "this will break a decman run" from "this is merely
stale", so a caller can abort on one and carry on past the other:

    0   Every package is valid and current.
    1   At least one package has an error: a PKGBUILD that does not parse,
        fails validation, or trips namcap. decman will fail to build it.
    2   No errors, but at least one warning: a package is behind upstream,
        declares no upstream to check, or could not be looked up. Everything
        still builds.

Errors outrank warnings: a run with both exits 1.

Note: reading a PKGBUILD's metadata runs `makepkg --printsrcinfo`, which
sources the file. Only ever point this at PKGBUILDs from this repo.
"""

import argparse
import contextlib
import dataclasses
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator

# Exit codes. Callers such as `nosarch/source.py` use these to decide whether a
# finding is worth aborting a decman run over.
EXIT_OK: int = 0
EXIT_ERROR: int = 1
EXIT_WARNING: int = 2

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
PACKAGES_DIR: Path = REPO_ROOT / "nosarch" / "packages"

DIRECTIVE_PATTERN: re.Pattern[str] = re.compile(r"^#\s*nosarch-upstream:\s*(.+?)\s*$", re.MULTILINE)

# Lines of `namcap --list` look like "elfpaths  : Check about ELF files ...".
NAMCAP_RULE_PATTERN: re.Pattern[str] = re.compile(r"^(\S+)\s+: ", re.MULTILINE)

HTTP_TIMEOUT: int = 30
USER_AGENT: str = "nosarch-check-custom-packages"

# Remote sources must be pinned. A local file shipped next to the PKGBUILD
# cannot change under us, so 'SKIP' is legitimate there.
REMOTE_SOURCE_PREFIXES: tuple[str, ...] = ("http://", "https://", "ftp://", "git+", "svn+", "hg+")

# Fields every custom package in this repo is expected to set.
REQUIRED_FIELDS: tuple[str, ...] = ("pkgdesc", "url", "license", "arch")

# namcap rules that cannot be satisfied by a repackaged vendor binary: every
# one of them reports a property of an upstream ELF we do not compile and
# cannot change. Rule names come from `namcap --list`.
NAMCAP_EXCLUDED_RULES: tuple[str, ...] = (
    "elfpaths",  # the payload lives under /opt by design
    "elfunstripped",
    "elfexecstack",
    "elfgnurelro",
    "elfnopie",
    "elfnoshstk",
    "elftextrel",
    "rpath",
    "runpath",
)


@dataclasses.dataclass(frozen=True, slots=True)
class Upstream:
    """Where to look up the current upstream version of a package."""

    kind: str
    url: str
    selector: str | None = None


@dataclasses.dataclass(slots=True)
class Result:
    """Outcome of checking a single package directory."""

    name: str
    current_version: str | None = None
    upstream_version: str | None = None
    problems: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)

    @property
    def outdated(self) -> bool:
        if self.current_version is None or self.upstream_version is None:
            return False
        return vercmp(self.current_version, self.upstream_version) < 0

    @property
    def has_errors(self) -> bool:
        """Whether this package would break a decman run."""
        return bool(self.problems)

    @property
    def has_warnings(self) -> bool:
        """Whether this package still builds but wants attention."""
        return bool(self.warnings) or self.outdated


def vercmp(left: str, right: str) -> int:
    """Compares two versions the way pacman does. Negative if `left` is older."""
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["vercmp", left, right], capture_output=True, text=True, check=True
        )
        return int(completed.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        # Without vercmp the best available answer is "equal unless textually different".
        return 0 if left == right else -1


def _running_as_root() -> bool:
    return os.geteuid() == 0


def _drop_to_nobody() -> None:
    """
    `preexec_fn` that switches a subprocess from root to the `nobody` user.

    Matches decman's own approach to parsing a PKGBUILD (see
    `decman.plugins.aur.package._srcinfo_from_pkgbuild_directory`): makepkg
    refuses outright to run as root, even just to print metadata, so when
    this script itself runs as root (invoked from `nosarch/source.py`, which
    decman runs as root) every `makepkg` call must drop privileges first.
    """
    nobody = pwd.getpwnam("nobody")
    os.setgid(nobody.pw_gid)
    os.setuid(nobody.pw_uid)


@contextlib.contextmanager
def _buildable_copy(package_dir: Path) -> Iterator[Path]:
    """
    A directory `nobody` can read and write, containing this package's files.

    Only makes a copy when actually running as root: `nobody` cannot be
    trusted to read an arbitrary path in the repo (permissions, ACLs), but a
    normal, non-root invocation already owns `package_dir` and can use it
    directly, exactly as this script did before it had to worry about root.
    """
    if not _running_as_root():
        yield package_dir
        return

    with tempfile.TemporaryDirectory(prefix="nosarch-pkgcheck-src-") as tmpdir:
        shutil.copytree(package_dir, tmpdir, dirs_exist_ok=True)

        mode = 0o777
        for root, dirs, files in os.walk(tmpdir):
            for name in dirs + files:
                os.chmod(os.path.join(root, name), mode)
        os.chmod(tmpdir, mode)

        yield Path(tmpdir)


def package_dirs(only: list[str]) -> list[Path]:
    """Every directory under `nosarch/packages/` holding a PKGBUILD."""
    if not PACKAGES_DIR.is_dir():
        return []

    found: list[Path] = sorted(entry for entry in PACKAGES_DIR.iterdir() if (entry / "PKGBUILD").is_file())

    if only:
        found = [entry for entry in found if entry.name in only]

    return found


def read_srcinfo(package_dir: Path) -> dict[str, list[str]]:
    """
    Parses a PKGBUILD's metadata via `makepkg --printsrcinfo`.

    Values are collected per key, since keys such as `depends` and
    `sha256sums` legitimately repeat.
    """
    with _buildable_copy(package_dir) as build_dir:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["makepkg", "--printsrcinfo"],
            cwd=build_dir,
            capture_output=True,
            text=True,
            check=True,
            preexec_fn=_drop_to_nobody if _running_as_root() else None,
        )

    fields: dict[str, list[str]] = {}

    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        fields.setdefault(key.strip(), []).append(value.strip())

    return fields


def read_upstream(package_dir: Path) -> Upstream | None:
    """Parses the `# nosarch-upstream:` directive out of a PKGBUILD, if present."""
    match: re.Match[str] | None = DIRECTIVE_PATTERN.search((package_dir / "PKGBUILD").read_text())

    if match is None:
        return None

    parts: list[str] = match.group(1).split()

    if len(parts) < 2:
        return None

    kind: str = parts[0]

    if kind == "github":
        return Upstream(kind=kind, url=f"https://api.github.com/repos/{parts[1]}/releases/latest")

    if len(parts) < 3:
        return None

    return Upstream(kind=kind, url=parts[1], selector=" ".join(parts[2:]))


def fetch(url: str) -> str:
    """GETs a URL and returns the body as text."""
    request: urllib.request.Request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return response.read().decode()


def upstream_version(upstream: Upstream) -> str:
    """Resolves the current upstream version. Raises `ValueError` if it cannot."""
    body: str = fetch(upstream.url)

    if upstream.kind == "github":
        tag: Any = json.loads(body).get("tag_name")

        if not isinstance(tag, str):
            raise ValueError("release JSON has no 'tag_name'")

        return tag.lstrip("v")

    if upstream.kind == "json":
        assert upstream.selector is not None
        value: Any = json.loads(body)

        for key in upstream.selector.split("."):
            if not isinstance(value, dict) or key not in value:
                raise ValueError(f"JSON has no key '{upstream.selector}'")
            value = value[key]

        if not isinstance(value, (str, int, float)):
            raise ValueError(f"'{upstream.selector}' is not a scalar")

        return str(value)

    if upstream.kind == "regex":
        assert upstream.selector is not None
        match: re.Match[str] | None = re.search(upstream.selector, body)

        if match is None or not match.groups():
            raise ValueError(f"pattern '{upstream.selector}' matched nothing")

        return match.group(1)

    raise ValueError(f"unknown upstream kind '{upstream.kind}'")


def validate(package_dir: Path, fields: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """
    Structural checks that need neither the network nor a build.

    Returns (problems, warnings).
    """
    problems: list[str] = []
    warnings: list[str] = []

    names: list[str] = fields.get("pkgname", [])

    if package_dir.name not in names:
        problems.append(f"directory is named '{package_dir.name}' but PKGBUILD builds {names or ['nothing']}")

    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            problems.append(f"missing '{field}'")

    sources: list[str] = fields.get("source", [])
    checksums: list[str] = []

    # Any of the supported digests is fine, but exactly one kind should be used.
    digests: list[str] = [key for key in fields if key.endswith("sums")]

    for key in digests:
        checksums.extend(fields[key])

    if sources and not digests:
        problems.append("sources are declared without any checksums")

    if len(digests) > 1:
        warnings.append(f"multiple checksum types declared: {', '.join(sorted(digests))}")

    if sources and checksums and len(sources) != len(checksums):
        problems.append(f"{len(sources)} source(s) but {len(checksums)} checksum(s)")

    for source, checksum in zip(sources, checksums):
        url: str = source.partition("::")[2] or source

        if checksum.upper() == "SKIP" and url.startswith(REMOTE_SOURCE_PREFIXES):
            problems.append(f"remote source is unpinned (checksum is SKIP): {url}")

        if url.startswith("http://"):
            warnings.append(f"source is fetched over plain HTTP: {url}")

    if "any" not in fields.get("arch", []) and not fields.get("pkgver"):
        problems.append("missing 'pkgver'")

    return problems, warnings


def namcap_rules() -> set[str]:
    """Every rule name namcap knows about, from `namcap --list`."""
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["namcap", "--list"], capture_output=True, text=True, check=False
    )

    return {
        match.group(1)
        for match in NAMCAP_RULE_PATTERN.finditer(completed.stdout)
    }


def run_namcap(target: Path) -> list[str]:
    """Runs namcap against a PKGBUILD or a built package, minus the expected noise."""
    # namcap's own `--exclude` drops only the *last* rule in the list: it calls
    # `active_modules.update(modules)` inside the per-rule loop, re-adding
    # everything it just removed (see /usr/lib/python3*/site-packages/namcap.py).
    # `--rules` has no such bug, so select the complement instead.
    rules: set[str] = namcap_rules() - set(NAMCAP_EXCLUDED_RULES)

    if not rules:
        return ["could not determine namcap's rule list"]

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["namcap", f"--rules={','.join(sorted(rules))}", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )

    findings: list[str] = []

    for line in completed.stdout.splitlines():
        stripped: str = line.strip()

        # namcap reports at three levels; only E is actionable here.
        if not stripped or " E: " not in stripped:
            continue

        # Every line is prefixed with the file namcap was given and the package
        # name, both of which the report header already shows.
        findings.append(f"namcap: {stripped.partition(' E: ')[2]}")

    return findings


def build_and_audit(package_dir: Path) -> list[str]:
    """
    Builds the package into a scratch directory and runs namcap on the result.

    This is the only way to get namcap's `depends` analysis, which is what
    catches a PKGBUILD that under- or over-declares its dependencies.
    """
    with (
        _buildable_copy(package_dir) as build_dir,
        tempfile.TemporaryDirectory(prefix="nosarch-pkgcheck-out-") as scratch,
    ):
        # `nobody` needs write access to wherever the build writes output, same
        # as the source copy above.
        if _running_as_root():
            os.chmod(scratch, 0o777)

        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["makepkg", "--force", "--clean", "--nodeps"],
            cwd=build_dir,
            capture_output=True,
            text=True,
            check=False,
            env={
                "PKGDEST": scratch,
                "SRCDEST": scratch,
                "BUILDDIR": scratch,
                "PATH": "/usr/bin",
                "HOME": scratch,
            },
            preexec_fn=_drop_to_nobody if _running_as_root() else None,
        )

        if completed.returncode != 0:
            tail: str = "\n".join(completed.stderr.strip().splitlines()[-5:])
            return [f"build failed:\n{tail}"]

        built: list[Path] = sorted(Path(scratch).glob("*.pkg.tar.*"))

        if not built:
            return ["build produced no package file"]

        findings: list[str] = []

        for package_file in built:
            findings.extend(run_namcap(package_file))

        return findings


def check(package_dir: Path, offline: bool, build: bool, have_namcap: bool) -> Result:
    """Runs every enabled check against one package directory."""
    result: Result = Result(name=package_dir.name)

    try:
        fields: dict[str, list[str]] = read_srcinfo(package_dir)
    except subprocess.CalledProcessError as error:
        tail: str = "\n".join(error.stderr.strip().splitlines()[-5:])
        result.problems.append(f"PKGBUILD does not parse:\n{tail}")
        return result
    except OSError:
        result.problems.append("could not run 'makepkg' (is pacman's base-devel installed?)")
        return result

    versions: list[str] = fields.get("pkgver", [])
    result.current_version = versions[0] if versions else None

    problems, warnings = validate(package_dir, fields)
    result.problems.extend(problems)
    result.warnings.extend(warnings)

    if have_namcap:
        result.problems.extend(run_namcap(package_dir / "PKGBUILD"))

        if build:
            result.problems.extend(build_and_audit(package_dir))

    if not offline:
        upstream: Upstream | None = read_upstream(package_dir)

        if upstream is None:
            result.warnings.append("no '# nosarch-upstream:' directive, cannot check freshness")
        else:
            try:
                result.upstream_version = upstream_version(upstream)
            except (urllib.error.URLError, OSError) as error:
                result.warnings.append(f"upstream lookup failed: {error}")
            except (ValueError, json.JSONDecodeError) as error:
                result.problems.append(f"upstream directive is broken: {error}")

    return result


def report(results: list[Result], quiet: bool) -> None:
    """Prints one block per package. When `quiet`, clean packages are omitted."""
    for result in results:
        if quiet and not (result.has_errors or result.has_warnings):
            continue

        if result.outdated:
            status: str = f"OUTDATED  {result.current_version} -> {result.upstream_version}"
        elif result.problems:
            status = "INVALID"
        elif result.upstream_version is not None:
            status = f"ok        {result.current_version} (current)"
        else:
            status = f"ok        {result.current_version}"

        print(f"  {result.name:<28} {status}")

        for problem in result.problems:
            for line in problem.splitlines():
                print(f"      ERROR: {line}")

        for warning in result.warnings:
            print(f"      warning: {warning}")


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="check_custom_packages.py",
        description="Checks the PKGBUILDs under nosarch/packages/ for freshness and correctness.",
    )
    _ = parser.add_argument("-p", "--package", action="append", default=[], help="check only this package")
    _ = parser.add_argument("-o", "--offline", action="store_true", help="skip upstream version checks")
    _ = parser.add_argument("-b", "--build", action="store_true", help="build each package so namcap can audit depends")
    _ = parser.add_argument(
        "-q", "--quiet", action="store_true", help="only print packages that have something to report"
    )
    args: argparse.Namespace = parser.parse_args()

    directories: list[Path] = package_dirs(args.package)

    if not directories:
        if not args.quiet:
            print("[PACKAGES] No custom packages found.")
        return EXIT_OK

    have_namcap: bool = shutil.which("namcap") is not None

    if not args.quiet:
        if not have_namcap:
            print("[PACKAGES] NOTE: namcap is not installed, skipping PKGBUILD linting.")
            print("[PACKAGES]       Install it with: pacman -S namcap")
        elif not args.build:
            print("[PACKAGES] NOTE: pass --build to let namcap audit 'depends'.")

    results: list[Result] = [check(directory, args.offline, args.build, have_namcap) for directory in directories]

    report(results, args.quiet)

    errored: list[Result] = [result for result in results if result.has_errors]
    warned: list[Result] = [result for result in results if result.has_warnings]

    # Errors outrank warnings: a package that cannot build matters more than a
    # package that is merely behind upstream.
    if errored:
        print(f"[PACKAGES] ERROR: {len(errored)} of {len(results)} custom package(s) will not build.")
        return EXIT_ERROR

    if warned:
        print(f"[PACKAGES] WARNING: {len(warned)} of {len(results)} custom package(s) need attention.")
        return EXIT_WARNING

    if not args.quiet:
        print("[PACKAGES] SUCCESS: All custom packages are current and valid.")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
