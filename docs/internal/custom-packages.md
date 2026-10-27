# Custom Packages

Custom packages install an app as an ordinary pacman package, so the engine manages it the same way as anything else.
They cover what neither the Arch repositories nor a trustworthy AUR package provides: AppImages,
`curl https://... | bash` installers, and vendor tarballs.

The PKGBUILDs live in their own repository, [NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages), one
directory per package under `packages/`.

## Declaring them

A module declares a package by name with `@aur.custom_packages`:

```python
from engine.steps import aur

@aur.custom_packages
def custom_pkgs(self) -> set[str]:
    custom_pkgs: set[str] = set()

    if "cursor-cli" in self._agents:
        custom_pkgs.add("cursor-cli-nosarch")

    return custom_pkgs
```

The name is the `pkgname`, which is also the directory name in NosArch-Packages, so the two cannot drift.

Every package is suffixed `-nosarch`. AUR helpers key off names, so a package called `cursor-cli` would be recognized
as the AUR's and replaced by it.

## How the PKGBUILDs get here

`utils.custom_packages` downloads a tarball of the branch into `/var/lib/nosarch/packages`, on the first run and
whenever the branch has moved on. The engine asks it for a package's directory only when it needs the PKGBUILD: to
check for an upgrade, or to build. A dry run reads whatever is cached and never fetches, because the cache is
root-owned.

A failed fetch is a warning, not an error, when a cached copy exists: it is still a usable set of PKGBUILDs, so a run
without network still works and simply does not pick up a version bump.

Deciding whether anything changed is one `git ls-remote`, which returns a commit id, compared against the revision
recorded in the cache. So an unchanged branch costs one small request and no download.

No git history is kept, because nothing reads it. Custom packages are not offered for review the way AUR packages are:
they come from NosArch's own repository. Tarball member paths are checked before extraction, since it is remote input.

The cache is root-owned on purpose. The engine reads these PKGBUILDs as root and hands a copy to `aurbuilduser` to
build, who should not be able to change a PKGBUILD between those two steps.

## `nosarch-package update` does not update these

`nosarch-package update` runs `yay -Syu`, which does not touch custom packages. They are built from PKGBUILDs by
`nosarch/apply.py`, so a version bump in NosArch-Packages only reaches the system on the next apply.

This is worth knowing because the symptom is silent: the update reports success and the packages are still the old
version. Fixing it means building the packages and installing them from a pacman repo rather than as foreign packages,
which is a larger change than it looks.
