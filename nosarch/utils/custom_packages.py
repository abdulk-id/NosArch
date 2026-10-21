"""
Provides the PKGBUILDs of NosArch's custom packages, which live in their own repository.

The PKGBUILDs live in their own repository. Modules declare those packages as Decman custom packages and this module
provides the directory each PKGBUILD is built from.
"""

import io
import os
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import decman.core.output
from decman.plugins.aur import CustomPackage

# The PKGBUILDs, one directory per package.
REPO_URL: str = "https://github.com/abdulk-id/NosArch-Packages.git"

# GitHub's tarball host. A repository's owner, name, and branch are what identify the archive; `codeload` is the
# documented endpoint behind the "Download ZIP" link on a repository page.
ARCHIVE_URL: str = "https://codeload.github.com/abdulk-id/NosArch-Packages/tar.gz/{revision}"

# The branch to follow. A commit id works here too, and pins the packages to an exact state.
BRANCH: str = "master"

# Inside the packages repository, one directory per `pkgname`.
PACKAGES_SUBDIR: str = "packages"

# Root-owned. Decman reads these PKGBUILDs as root and hands them to `nobody` and `aurbuilduser`, and neither must be
# able to change a PKGBUILD between the two. Decman copies the directory into its build area before building, so the
# build user never reads this path directly.
CACHE_DIR: str = "/var/lib/nosarch/packages"

# Which revision the cached copy came from, so an unchanged branch costs no download. Inside the cache rather than
# beside it, so removing the cache removes the state that would disagree with it.
REVISION_FILE: str = os.path.join(CACHE_DIR, ".revision")

HTTP_TIMEOUT: int = 30
USER_AGENT: str = "nosarch-custom-packages"

# Resolved once per decman run. See ensure_packages().
_packages_dir: str | None = None


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Runs git, capturing output for the caller to report."""

    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _cached_revision() -> str | None:
    """The revision the cached PKGBUILDs came from, or None when there is nothing usable cached."""

    if not os.path.isdir(os.path.join(CACHE_DIR, PACKAGES_SUBDIR)):
        return None

    try:
        with open(REVISION_FILE, encoding="utf-8") as file:
            revision: str = file.read().strip()
    except OSError:
        # A cache without a recorded revision predates this file. Its contents cannot be identified, so treat it as
        # unusable rather than trusting files of unknown origin.
        return None

    return revision or None


def _remote_revision() -> str:
    """
    The commit id the branch currently points at.

    `git ls-remote` rather than the GitHub API: the API needs no token for a public repository but is rate limited to
    a few dozen requests an hour per address, and a shared or CI address can exhaust that. This asks git directly and
    answers with a commit id and nothing else.
    """

    completed: subprocess.CompletedProcess[str] = _git("ls-remote", "--exit-code", REPO_URL, f"refs/heads/{BRANCH}")

    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git ls-remote exited {completed.returncode}")

    fields: list[str] = completed.stdout.split()
    if not fields:
        raise RuntimeError(f"{REPO_URL} has no branch named {BRANCH!r}")

    return fields[0]


def _download(revision: str) -> bytes:
    url: str = ARCHIVE_URL.format(revision=revision)

    request: urllib.request.Request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"could not fetch {url}: {error}") from error


def _extract(archive: bytes, destination: str) -> None:
    """
    Unpacks a GitHub tarball into `destination`.

    Every entry in such an archive sits under one directory named after the repository and revision, which is stripped
    so the caller gets the repository's own layout. Member paths are checked rather than trusted: a tarball is remote
    input, and a member named `../..` or an absolute path would write outside `destination`.
    """

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if os.path.isabs(member.name):
                raise RuntimeError(f"unsafe archive entry {member.name!r}")

            parts: tuple[str, ...] = Path(member.name).parts

            # The first component is the repository directory every member shares. The archive also carries that
            # directory as its own entry, which has no second component to strip.
            if len(parts) < 2:
                if not member.isdir():
                    raise RuntimeError(f"unexpected archive entry {member.name!r}")
                continue

            if parts[0] in ("", ".", ".."):
                raise RuntimeError(f"unsafe archive entry {member.name!r}")

            relative: str = os.path.join(*parts[1:])
            if relative.startswith("..") or os.path.isabs(relative):
                raise RuntimeError(f"unsafe archive entry {member.name!r}")

            if member.isdir():
                os.makedirs(os.path.join(destination, relative), mode=0o755, exist_ok=True)
            elif member.isfile():
                target: str = os.path.join(destination, relative)
                os.makedirs(os.path.dirname(target), mode=0o755, exist_ok=True)

                source = tar.extractfile(member)
                if source is None:
                    raise RuntimeError(f"could not read archive entry {member.name!r}")

                with source, open(target, "wb") as file:
                    file.write(source.read())

            # Symlinks and devices are not expected from GitHub, and are skipped rather than created.


def _install(revision: str) -> None:
    """
    Fetches `revision` and makes it the cached copy, replacing whatever was there.

    Extracted to a sibling and moved into place, so a download or unpack that fails leaves the previous PKGBUILDs
    intact. A half-extracted tree would be built from, which is worse than building a slightly old package.
    """

    staging: str = f"{CACHE_DIR}.new"

    # A leftover from an interrupted run would otherwise make the rename below fail.
    shutil.rmtree(staging, ignore_errors=True)

    try:
        os.makedirs(staging, mode=0o755, exist_ok=True)
        _extract(_download(revision), staging)

        if not os.path.isdir(os.path.join(staging, PACKAGES_SUBDIR)):
            raise RuntimeError(f"archive has no {PACKAGES_SUBDIR}/ directory")

        with open(os.path.join(staging, ".revision"), "w", encoding="utf-8") as file:
            file.write(revision + "\n")

        # Replaces the directory in one step, so the cache is never briefly absent.
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)

        os.rename(staging, CACHE_DIR)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _update() -> None:
    cached: str | None = _cached_revision()

    try:
        remote: str = _remote_revision()
    except RuntimeError as error:
        if cached is None:
            raise SystemExit(f"Could not fetch custom packages from {REPO_URL}: {error}")

        # Not fatal: the cached PKGBUILDs are still a usable set, so a run without network still works. It just does
        # not pick up a version bump, and the user is told which revision they are building.
        decman.core.output.print_warning(
            f"Could not check custom packages for updates: {error}. Using cached revision {cached}."
        )
        return

    if cached == remote:
        return

    decman.core.output.print_info(f"Fetching custom packages at {remote[:12]}")

    try:
        _install(remote)
    except RuntimeError as error:
        if cached is None:
            raise SystemExit(f"Could not fetch custom packages from {REPO_URL}: {error}")

        decman.core.output.print_warning(f"Could not update custom packages: {error}. Using cached revision {cached}.")


def ensure_packages() -> str:
    """
    Makes sure the PKGBUILDs are on disk and returns the directory holding them, one subdirectory per package.

    Downloads on the first run and when the branch has moved on since. Callers get the same path every run, so a
    module declaring a package resolves to the same directory whether or not this had to fetch anything.

    Memoized because a module calls this once per declared package, and an uncached version fetched on every call
    would hit the network once per package to learn about one repository.
    """

    global _packages_dir

    if _packages_dir is None:
        _update()
        _packages_dir = os.path.join(CACHE_DIR, PACKAGES_SUBDIR)

    return _packages_dir


def package_dir(pkgname: str) -> str:
    """The directory holding one package's PKGBUILD, for Decman's `pkgbuild_directory`."""

    return os.path.join(ensure_packages(), pkgname)


def package(pkgname: str) -> CustomPackage:
    """Declares one custom package for a module, from its PKGBUILD in the packages repository."""

    return CustomPackage(pkgname=pkgname, pkgbuild_directory=package_dir(pkgname))
