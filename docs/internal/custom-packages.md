# Custom Packages

Custom packages install an app as an ordinary pacman package, so decman manages it the same way as anything else. They
cover what neither the Arch repositories nor a trustworthy AUR package provides: AppImages, `curl https://... | bash`
installers, and vendor tarballs.

The PKGBUILDs live in their own repository, [NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages), one
directory per package under `packages/`.

## Declaring them

A module declares a package with `@aur.custom_packages`, returning `utils.custom_packages.package(...)`:

```python
import utils.custom_packages
from decman.plugins import aur

@aur.custom_packages
def custom_pkgs(self) -> set[aur.CustomPackage]:
    custom_pkgs: set[aur.CustomPackage] = set()

    if "cursor-cli" in self._agents:
        custom_pkgs.add(utils.custom_packages.package("cursor-cli-nosarch"))

    return custom_pkgs
```

The name is the `pkgname`, which is also the directory name in NosArch-Packages, so the two cannot drift.

Every package is suffixed `-nosarch`. AUR helpers key off names, so a package called `cursor-cli` would be recognized
as the AUR's and replaced by it.

## How the PKGBUILDs get here

`utils.custom_packages` downloads a tarball of the branch into `/var/lib/nosarch/packages`, on the first run and
whenever the branch has moved on, and hands decman the directory for the package it asked for.

A failed fetch is a warning, not an error, when a cached copy exists: it is still a usable set of PKGBUILDs, so a run
without network still works and simply does not pick up a version bump.

Deciding whether anything changed is one `git ls-remote`, which returns a commit id, compared against the revision
recorded in the cache. So an unchanged branch costs one small request and no download.

No git history is kept, because nothing reads it. Decman copies the PKGBUILD directory into its build area and builds
from it, and its review step pages the files rather than diffing commits. Tarball member paths are checked before
extraction, since it is remote input.

That module exists because decman's own `git_url` option cannot be used here. Decman clones the URL and reads the
`PKGBUILD` at the **root** of the clone, and raises `PKGBUILDParseError` if there is none. NosArch-Packages holds one
directory per package, so every `git_url` would fail.

> Do not "simplify" this to `git_url`. Sparse-checkout can reach a single package's directory out of the same
> repository, but decman clones without it and still reads the root `PKGBUILD`, so it does not help. The only layouts
> that work are a local copy, or one repository per package.

The cache is root-owned on purpose. Decman reads these PKGBUILDs as root and hands them to `nobody` and
`aurbuilduser` to build. Neither should be able to change a PKGBUILD between those two steps.

## `nosarch-package update` does not update these

`nosarch-package update` runs `yay -Syu`, which does not touch custom packages. They are built from PKGBUILDs by decman,
so a version bump in NosArch-Packages only reaches the system on the next decman run.

This is worth knowing because the symptom is silent: the update reports success and the packages are still the old
version. Fixing it means building the packages and installing them from a pacman repo rather than as foreign packages,
which is a larger change than it looks.
