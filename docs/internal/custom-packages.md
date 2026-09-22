# Custom packages

For apps which do not have an Arch or Homebrew package, a custom package should be used. This custom package
implementation allows installing AppImages, vendor tarballs, or payloads behind `curl https://... | bash` installers.
Custom packages allows installing these as Arch packages that decman and pacman can manage.

## Why not the AUR

- **Security**: The PKGBUILD is managed by us. For a repackaged binary, we manage a URL and a checksum, which is
  easier to audit than an unfamiliar maintainer's build script. The checksum is a guarantee `curl | bash` cannot
  offer, since an install script fetches whatever is at the URL at the time.
- **Reliability**: Nothing resolves through the AUR, so a package cannot be orphaned or deleted out from under a run.

The cost is that we have to manage version bumps. `tools/check_custom_packages.py` checks for outdated versions and
find the latest version to bump to.

## Adding a custom package

A custom package is a PKGBUILD kept in this repo under `nosarch/packages/`.

### 1. Create the directory

One directory per package under `nosarch/packages/`, named exactly as the `pkgname` it builds.

To avoid name collisions with packages from the AUR, suffix the name with `-nosarch`. So if there is a name collision,
AUR helpers would not assume it is an AUR package and try to update it themselves.

### 2. Get the download URL and its checksum

The goal is always the same regardless of upstream's distribution method: find the actual file(s) `package()` needs to
fetch, and pin each with a checksum.

- **AppImage or tarball**: the download URL is the artifact itself.

    ```sh
    curl --location --output example.AppImage "<url>"
    sha256sum example.AppImage
    ```

- **`curl https://... | bash` installer**: Read the installer script to find the URL(s) it fetches (a `.deb`, tarball,
  or binary), and pin those instead. If the script builds the URL from a version string, that version is what
  [step 4](#4-declare-where-upstream-lives)'s directive needs to track.

    ```sh
    curl --location "<installer-url>" | less   # read it, don't run it
    curl --location --output example.tar.gz "<real-payload-url-found-in-script>"
    sha256sum example.tar.gz
    ```

Keep every hash to pin them so if the bytes at a pinned URL ever change, the build fail instead of installing
something unexpected.

### 3. Write the PKGBUILD

Match the existing custom package PKGBUILDs.

### 4. Declare where upstream lives

Add one directive comment near the top of the PKGBUILD so the checker can tell when the package version is old:

```bash
# nosarch-upstream: github <owner>/<repo>
# nosarch-upstream: json https://example.com/api/latest version
# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'
```

| Form                      | Use when                          | Notes                                                                                     |
| ------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------- |
| `github <owner>/<repo>`   | The app has GitHub releases       | Reads `tag_name`, strips a leading `v`.                                                   |
| `json <url> <dotted.key>` | The vendor has an update endpoint | Find it with Browser DevTools' Network tab on their download page, filtered to XHR/Fetch. |
| `regex <url> <pattern>`   | Neither of the above              | One capture group. Brittle — vendors restyle pages.                                       |

The directive is optional. Without it the package is never version-checked.

#### Regex directive

The checker fetches `<url>` as plain text (the raw HTML, not rendered) and runs `<pattern>` against it as a Python
regex. Whatever the single capture group `(...)` matches is treated as the current upstream version.

Example: a vendor's download page contains `href="/dl/Example-2.4.1-x86_64.AppImage"`. The directive
`# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'` matches that text and captures
`2.4.1`.

Keep exactly one capture group as the checker uses group 1 and ignores the rest of the match.

If the page renders its download links client-side (nothing but a JS bundle in the raw HTML), `regex` cannot see them.
In that case, look for a `json` endpoint the page calls instead.

### 5. Wire it into a module

Declare it in whichever module owns the app. Example:

```python
import os
from decman.plugins import aur

# decman reads `source.py` as text and `exec()`s it after `os.chdir`-ing into its
# directory, so package paths resolve relative to `nosarch/`, not to this file.
_PACKAGES_DIR: str = os.path.abspath("packages")


    @aur.custom_packages
    def custom_pkgs(self) -> set[aur.CustomPackage]:
        return {
            aur.CustomPackage(
                pkgname="example-appimage",
                pkgbuild_directory=os.path.join(_PACKAGES_DIR, "example-appimage"),
            )
        }
```

### 6. Check it

```sh
python3 tools/check_custom_packages.py --build
```

pass `--build` so namcap can audit `depends` (slower process).

Then review what paths the package actually installs to, so an unexpected path stands out:

```sh
pacman --query --list --file *.pkg.tar.zst
```

## The checker

`tools/check_custom_packages.py` checks whether each `pkgver` is behind upstream, and whether the PKGBUILD itself is
sound (structural checks and namcap audits).

The checker exits with the following codes

| Exit Code | Meaning                                                                                                                        |
| --------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `0`       | Every package is valid and current.                                                                                            |
| `1`       | At least one package has an **error**: it does not parse, fails validation, or trips namcap. decman will fail to build it.     |
| `2`       | No errors, but at least one **warning**: behind upstream, no upstream declared, or the lookup failed. Everything still builds. |

Errors outrank warnings; a run with both exits `1`.

Flags:

- `--offline` skips every network lookup,
- `--quiet` prints only packages with something to report,
- `--package NAME` narrows to one specific package

## Bumping a version

1. Run the checker; it names the packages that are behind and the version upstream is on.
2. Update `pkgver`, any `_commit`-style variable, and `sha256sums` (re-download, re-hash).
3. Reset `pkgrel` to `1`. Bump `pkgrel` instead of `pkgver` when only the recipe changed.
4. Re-run the checker with `--build`.

## Gotchas

- **Pin every remote source**: `SKIP` in `sha256sums` is legitimate only for files shipped alongside the PKGBUILD.
  The checker treats `SKIP` on an `http(s)`/`git+` source as an error.
- **`LicenseRef-` obliges you to ship the license**: A non-standard license identifier requires the license text under
  `/usr/share/licenses/$pkgname/`, or namcap fails the package. Vendor archives usually contain one. Extract it in
  `prepare()` and install it in `package()`.
- **Not every AppImage bundles a `.desktop` entry and icons**: Run `--appimage-extract` by hand once and look before
  assuming they are there. Also check that the desktop entry's `Icon=` name matches the icon files it ships.
- **Expect namcap noise on repackaged binaries**: Unstripped ELFs, files outside FHS paths, and missing hardening
  flags are properties of a binary we did not compile. The checker already excludes those rules. Do not "fix" them in
  the PKGBUILD.
