# Releasing

A release is a GitHub release with two files: `nosarch-source.pkg.tar.zst` (the pacman package) and `SHA256SUMS`.
[`install.sh`](../../install.sh) downloads the package and runs `pacman -U` on it. It does not apply NosArch.

A release is made only when you decide to. Nothing is published on a push or on a schedule.

## Making a release

Both ways run the same script, [`utils/release.py`](../../utils/release.py), so they make the same release.

| Release | Command              | Is `releases/latest` |
| :------ | :------------------- | :------------------- |
| Stable  | `mise release 0.1.0` | yes                  |
| Dev     | `mise release dev`   | never                |

**On your machine.** It needs Arch (`makepkg`), `gh auth login`, `python` and `python-pytest`. Use this when GitHub
Actions is down.

**On GitHub.** Actions > Release > Run workflow, then pick `stable` or `dev`. It runs the script in an Arch container.
Run it from `master`.

The script:

1. Stops unless you are on `master`, the tree is clean, and `HEAD` is `origin/master`. What is released is exactly
   what is on `master`.
2. Works out the tag and the package version (below), and stops if the tag already exists.
3. Runs the tests, builds the package with `makepkg`, and writes the checksum.
4. Publishes the release as a draft, uploads the two files, and then publishes it.

`mise release --dry-run dev` does everything except step 4, and a failed check in step 1 only warns. Use it to try the
script on a branch. It keeps the build and prints where.

If the script stops during step 4, a draft release is left behind. Run it again, and it replaces the draft.

## Versions

A stable version is `X.Y.Z`, tagged `vX.Y.Z`.

NosArch is currently alpha, so every version is `0.Y.Z`.

A dev build is named for the stable version it leads to, then the date and the day's count:
`v0.2.0-dev-20261114-1`. The date is `yyyymmdd`, so names sort in order. The count is how many dev builds for that
version were made that day, plus one. The version it leads to is the latest stable version with its minor bumped, or
`0.1.0` before the first release. `mise release dev --next 0.1.1` names another one.

A dev build is a GitHub prerelease. GitHub's `releases/latest` skips prereleases, so the plain install command never
installs one.

The tag is the version, so a release needs no commit. The script passes the version to
[`PKGBUILD`](../../packaging/arch/PKGBUILD), and pacman rejects a hyphen in a version, so the dev build above is
`0.2.0dev.20261114.1`. It sorts before `0.2.0` and after the previous stable version. A build made with `mise pkg-arch`
is `0.0.0.rN.gSHA`.

A tag cannot be moved after a release is published from it. If a release is wrong, delete the release and the tag, fix
it, and release again, or release the next patch.

## Installing

```sh
# the latest stable version
curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh
# the newest dev build
curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh -s -- --dev
# one release
curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh -s -- v0.2.0-dev-20261114-1
```

With no argument the script installs the latest stable release. `--dev` installs the newest dev build (`dev` means the
same). A tag installs that release. Editing `install.sh` changes the installer for every release, including ones
already published. The package it downloads is still the package from that release.

It finds the latest stable release by following `releases/latest`. GitHub redirects that to the release's page, and to
the release list when there is no stable release. That is a page request, so it does not use the API limit. `--dev`
asks the GitHub API for the newest prerelease. That is one anonymous request, and GitHub allows 60 an hour per address.
The parsing is a few lines of `awk` over the API's output, which assumes the JSON is indented the way GitHub sends it.

The package and `SHA256SUMS` are then downloaded from that release. Both files come from the tag it resolved, so they
stay a pair if another release is published during the download.

The installer also writes the smallest `~/.nosarch_config.json` NosArch accepts, `{"user": {"username": ...}}`, if
there is none. The username is the account that runs it, or the one that ran it with `sudo`. An existing config is never
overwritten. A plain root login writes nothing. Everything else in the config has a default, including `user.fullname`
and `user.git_email`, which only fill in Git's `user.name` and `user.email`. Keep the schema's required fields and
`tests/test_config_schema.py` in step with what the installer writes.

Running it again installs the same version again, which is how a throwaway VM is reset.

## The package

The package installs the `nosarch/` tree to `/usr/lib/nosarch/nosarch/` and a launcher to `/usr/bin/nosarch-apply`.
It is not a Python wheel in `site-packages`. That directory is named for the Python minor version, and a release
asset is never rebuilt when Arch moves to the next one. After `pacman -Syu` the package would stop importing. The
engine has no dependencies, so the tree runs where it is, and `__main__.py` already puts its parent on the path and
restarts itself as root by file path.

The files are tracked and not-ignored files under `nosarch/`, so a local build includes a new file before it is
committed and no build includes a cache. The file is named `nosarch-source.pkg.tar.zst` for every release, so the
installer needs no GitHub API call for a stable install. Pacman takes the package name and version from inside it.

`mise pkg-arch` builds the package from the checkout. Check what it holds:

```sh
pacman -Qip packaging/arch/nosarch-*.pkg.tar.zst
bsdtar -tvf packaging/arch/nosarch-*.pkg.tar.zst
```

## Why it is built this way

- **One script.** The Action only runs it. Two copies of the build and publish steps would drift apart, and the
  fallback would stop being the same release.
- **The release is a draft until the files are up.** `releases/latest` points at a release the moment it is
  published, and an upload takes seconds. Without the draft, an install in that window finds a release with no
  package.
- **The Action has no push or schedule trigger.** A release is a decision. Only `workflow_dispatch` starts one.

## Trust

`SHA256SUMS` catches a corrupted or truncated download. It does not catch a replaced release: whoever can replace the
package can replace the checksum. If that matters later, sign the package with GPG or publish GitHub build
attestations.
