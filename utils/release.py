"""Build master and publish it as a GitHub release. See docs/operations/release.md.

`mise release` runs this file, and so does the Release workflow. Run it yourself when GitHub Actions is down.

    mise release 0.1.0                  a stable version
    mise release dev                    a dev build, named for the stable version it leads to
    mise release dev --next 0.1.1       the same, leading to 0.1.1 instead of the next minor version
    mise release --dry-run <the above>  everything except publishing, and a failed check only warns

It needs git, gh (logged in), makepkg, python and pytest.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO: str = "abdulk-id/NosArch"
PACKAGE: str = "nosarch-source.pkg.tar.zst"
ROOT: Path = Path(__file__).resolve().parents[1]

Version = tuple[int, int, int]


class ReleaseError(Exception):
    """Something stops the release. The message says what to do."""


@dataclass(frozen=True)
class Arguments:
    kind: str  # "stable" or "dev"
    version: str  # the version asked for, for a stable release
    next_version: str  # the version a dev build leads to, when it is not the next minor version
    dry_run: bool


@dataclass(frozen=True)
class Plan:
    kind: str
    tag: str
    package_version: str
    title: str
    leads_to: str  # the stable version a dev build leads to, empty for a stable release


# Utilities ---


def run(
    command: list[str], *, capture: bool = False, directory: Path = ROOT, environment: dict[str, str] | None = None
) -> str:
    """Run a command. A failure raises. Output is returned, or streamed when it is not captured."""
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        command, cwd=directory, env=environment, check=False, text=True, capture_output=capture
    )
    if completed.returncode != 0:
        detail: str = f"\n{completed.stderr.strip()}" if capture and completed.stderr else ""
        raise ReleaseError(f"`{' '.join(command)}` failed with exit code {completed.returncode}.{detail}")
    return completed.stdout.strip() if capture else ""


def git(*arguments: str) -> str:
    return run(["git", *arguments], capture=True)


def step(heading: str) -> None:
    print(f"\n{heading}", flush=True)


def format_version(version: Version) -> str:
    return ".".join(str(part) for part in version)


def parse_version(text: str) -> Version:
    match: re.Match[str] | None = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text)
    if match is None:
        raise ReleaseError(f"'{text}' is not a version: use X.Y.Z, such as 0.1.0.")
    return int(match[1]), int(match[2]), int(match[3])


# Features ---


def check_tools(dry_run: bool) -> None:
    for tool in ["git", "makepkg", "pacman"] + ([] if dry_run else ["gh"]):
        if shutil.which(tool) is None:
            raise ReleaseError(f"{tool} is required.")
    if not dry_run and subprocess.run(["gh", "auth", "status"], capture_output=True, check=False).returncode != 0:
        raise ReleaseError("gh is not logged in. Run: gh auth login")


def check_state(dry_run: bool) -> None:
    """What is released is exactly master, whoever runs this. A dry run reports a problem and goes on."""
    problems: list[str] = []

    branch: str = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "master":
        problems.append(f"a release is made from master. This is {branch}.")
    if git("status", "--porcelain"):
        problems.append("the working tree has uncommitted changes.")
    git("fetch", "--quiet", "--tags", "origin")
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/master"):
        problems.append("HEAD is not origin/master. Pull or push first.")

    if problems and not dry_run:
        raise ReleaseError(problems[0])
    for problem in problems:
        print(f"release: a real run would stop: {problem}", file=sys.stderr)


def latest_stable(tags: list[str]) -> Version | None:
    versions: list[Version] = [parse_version(tag[1:]) for tag in tags if re.fullmatch(r"v\d+\.\d+\.\d+", tag)]
    return max(versions, default=None)


def make_plan(arguments: Arguments, tags: list[str], today: str) -> Plan:
    latest: Version | None = latest_stable(tags)

    if arguments.kind == "stable":
        version: Version = parse_version(arguments.version)
        if latest is not None and version <= latest:
            raise ReleaseError(
                f"{format_version(version)} is not newer than the latest version, {format_version(latest)}."
            )
        text: str = format_version(version)
        title: str = f"NosArch {text}" + (" (alpha)" if version[0] == 0 else "")
        return Plan("stable", f"v{text}", text, title, "")

    leads_to: Version
    if arguments.next_version:
        leads_to = parse_version(arguments.next_version)
    elif latest is None:
        leads_to = (0, 1, 0)
    else:
        leads_to = (latest[0], latest[1] + 1, 0)
    if latest is not None and leads_to <= latest:
        raise ReleaseError(
            f"a dev build leads to a version newer than {format_version(latest)}. {format_version(leads_to)} is not."
        )

    # The run is how many dev builds leading to this version were made today, plus one.
    target: str = format_version(leads_to)
    earlier: list[int] = [
        int(match[1]) for tag in tags if (match := re.fullmatch(rf"v{re.escape(target)}-dev-{today}-(\d+)", tag))
    ]
    run_number: int = max(earlier, default=0) + 1
    # Pacman rejects a hyphen in a version. `dev` sorts before the stable version, as a dev build should.
    return Plan(
        "dev",
        f"v{target}-dev-{today}-{run_number}",
        f"{target}dev.{today}.{run_number}",
        f"NosArch {target} dev build {today}-{run_number}",
        target,
    )


def release_state(tag: str) -> str:
    """ "published", "draft" or "none". A draft is left by a run that failed while uploading."""
    listing: str = run(
        ["gh", "release", "list", "--repo", REPO, "--limit", "200", "--json", "tagName,isDraft"], capture=True
    )
    for release in json.loads(listing):
        if release["tagName"] == tag:
            return "draft" if release["isDraft"] else "published"
    return "none"


def test() -> None:
    step("Testing")
    run([sys.executable, "tests/test_config_schema.py"])
    run([sys.executable, "-B", "-m", "pytest", "tests/engine", "-q"])


def build_package(plan: Plan, work: Path) -> Path:
    step("Building")
    built: Path = work / "built"
    (work / "build").mkdir()
    built.mkdir()
    environment: dict[str, str] = {
        **os.environ,
        "NOSARCH_VERSION": plan.package_version,
        "BUILDDIR": str(work / "build"),
        "PKGDEST": str(built),
    }
    run(
        ["makepkg", "--force", "--noconfirm", "--cleanbuild"],
        directory=ROOT / "packaging" / "arch",
        environment=environment,
    )

    packages: list[Path] = list(built.glob("nosarch-*-any.pkg.tar.zst"))
    if len(packages) != 1:
        raise ReleaseError("makepkg did not produce exactly one package.")
    information: str = run(["pacman", "--query", "--info", "--file", str(packages[0])], capture=True)
    match: re.Match[str] | None = re.search(r"^Version\s*:\s*(\S+)", information, re.MULTILINE)
    if match is None or match[1] != f"{plan.package_version}-1":
        raise ReleaseError(f"the package is {match[1] if match else 'unversioned'}, not {plan.package_version}-1.")
    return packages[0]


def stage_assets(plan: Plan, package: Path, work: Path) -> list[Path]:
    assets: Path = work / "assets"
    assets.mkdir()
    shutil.copy(package, assets / PACKAGE)

    digest: str = hashlib.sha256((assets / PACKAGE).read_bytes()).hexdigest()
    (assets / "SHA256SUMS").write_text(f"{digest}  {PACKAGE}\n")

    # The copy attached to the release installs that release, so the tag goes into it.
    script: str = (ROOT / "install.sh").read_text()
    stamped: str
    count: int
    stamped, count = re.subn(r"^baked_tag=.*$", lambda _: f'baked_tag="{plan.tag}"', script, flags=re.MULTILINE)
    if count != 1:
        raise ReleaseError("install.sh has no single baked_tag line to set.")
    (assets / "install.sh").write_text(stamped)
    (assets / "install.sh").chmod(0o755)

    return sorted(assets.iterdir())


def release_notes(plan: Plan, sha: str) -> str:
    install_command: str = f"curl -fsSL https://github.com/{REPO}/releases/download/{plan.tag}/install.sh | sh"
    intro: str = ""
    if plan.kind == "dev":
        intro = f"A dev build leading to {plan.leads_to}, made from {sha}. For testing, not for a machine you depend on.\n\n"
    elif plan.package_version.startswith("0."):
        intro = (
            "NosArch is alpha. An upgrade can need changes to `~/.nosarch_config.json` "
            "or to what the definition manages.\n\n"
        )
    return f"{intro}```sh\n{install_command}\n```\n"


def publish(plan: Plan, sha: str, assets: list[Path], notes: Path) -> None:
    """A draft is not visible at releases/latest. Publishing it once the files are up means an install never finds a
    release without its package."""
    step("Publishing")
    if release_state(plan.tag) == "draft":
        run(["gh", "release", "delete", plan.tag, "--repo", REPO, "--yes"])

    create: list[str] = [
        *["gh", "release", "create", plan.tag, "--repo", REPO, "--draft", "--target", sha],
        *["--title", plan.title, "--notes-file", str(notes)],
        *(["--prerelease"] if plan.kind == "dev" else ["--generate-notes"]),
        *[str(asset) for asset in assets],
    ]
    run(create)
    run(
        [
            "gh",
            "release",
            "edit",
            plan.tag,
            "--repo",
            REPO,
            "--draft=false",
            *(["--prerelease"] if plan.kind == "dev" else []),
        ]
    )


# main ---


def parse_arguments(argv: list[str]) -> Arguments:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Build master and publish it as a GitHub release.", epilog="See docs/operations/release.md."
    )
    parser.add_argument("target", metavar="dev|X.Y.Z", help="a dev build, or the stable version to release")
    parser.add_argument(
        "--next", dest="next_version", default="", metavar="X.Y.Z", help="the version a dev build leads to"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="do everything except publish, and only warn on a failed check"
    )
    parsed: argparse.Namespace = parser.parse_args(argv)

    if parsed.target == "dev":
        return Arguments("dev", "", parsed.next_version, parsed.dry_run)
    if parsed.next_version:
        parser.error("--next only applies to a dev build")
    return Arguments("stable", parsed.target.removeprefix("v"), "", parsed.dry_run)


def release(arguments: Arguments) -> None:
    check_tools(arguments.dry_run)
    check_state(arguments.dry_run)

    tags: list[str] = git("tag", "--list").splitlines()
    today: str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    plan: Plan = make_plan(arguments, tags, today)
    if plan.tag in tags or (not arguments.dry_run and release_state(plan.tag) == "published"):
        raise ReleaseError(f"{plan.tag} already exists.")

    sha: str = git("rev-parse", "HEAD")
    print(f"Release {plan.tag} (package version {plan.package_version}) from {git('log', '-1', '--format=%h %s')}")
    test()

    work: Path = Path(tempfile.mkdtemp())
    try:
        package: Path = build_package(plan, work)
        assets: list[Path] = stage_assets(plan, package, work)
        notes: Path = work / "notes.md"
        notes.write_text(release_notes(plan, sha))

        if arguments.dry_run:
            print(f"\nDry run: nothing was published. It would have published {plan.tag} with:")
            for asset in assets:
                print(f"  {asset.name}  {asset.stat().st_size} bytes")
            print(f"\nTitle: {plan.title}\n{notes.read_text()}\nThe build is kept in {work}")
            return

        publish(plan, sha, assets, notes)
        print(f"\nPublished https://github.com/{REPO}/releases/tag/{plan.tag}")
        print(f"Install it with:\n  curl -fsSL https://github.com/{REPO}/releases/download/{plan.tag}/install.sh | sh")
    finally:
        if not arguments.dry_run:
            shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    try:
        release(parse_arguments(sys.argv[1:]))
    except ReleaseError as error:
        print(f"release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
