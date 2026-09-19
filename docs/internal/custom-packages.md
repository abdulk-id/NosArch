# Custom packages

How to install an app that ships no Arch package — an AppImage, a vendor tarball, or the
payload behind a `curl | bash` installer — and have decman manage it like any other package.

## Why not the AUR

A custom package is a PKGBUILD kept in this repo under `nosarch/packages/`. decman builds it
in a clean chroot and hands the result to pacman, exactly as it would an AUR package. The
difference is where the recipe comes from:

- **Security.** The recipe is ours. For a repackaged binary it amounts to a URL and a
  checksum, which is far less to audit than an unfamiliar maintainer's build script — and
  the checksum is a guarantee `curl | bash` cannot offer, since an install script fetches
  whatever is at the URL today.
- **Reliability.** Nothing resolves through the AUR RPC, so a package cannot be renamed,
  orphaned, or deleted out from under a run.

The cost is that version bumps are ours too. `tools/check_custom_packages.py` exists to make
that cost visible rather than silent.

## Adding one

### 1. Create the directory

One directory per package under `nosarch/packages/`, named exactly as the `pkgname` it
builds. The checker enforces the match.

```sh
mkdir nosarch/packages/example-appimage
```

### 2. Get the download URL and its checksum

```sh
curl --location --output example.AppImage "<url>"
sha256sum example.AppImage
```

Keep the hash. Pinning it is the entire security argument for this approach: if the bytes at
that URL ever change, the build fails loudly instead of installing something new.

### 3. Write the PKGBUILD

Start from the template in `nosarch/packages/README.md`, which also explains what each field
means and how `$pkgdir` maps onto the installed filesystem. The short version: a PKGBUILD is
a shell script that sets some variables and defines `prepare()` and `package()`; `package()`
fills a fake root, and whatever path you create under `$pkgdir` is the path the file lands on
at install time.

### 4. Declare where upstream lives

Add one directive comment so the checker can tell when the package falls behind:

```bash
# nosarch-upstream: github <owner>/<repo>
# nosarch-upstream: json https://example.com/api/latest version
# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'
```

| Form                      | Use when                          | Notes                                                                             |
| ------------------------- | --------------------------------- | --------------------------------------------------------------------------------- |
| `github <owner>/<repo>`   | The app has GitHub releases       | Reads `tag_name`, strips a leading `v`. Try this first.                           |
| `json <url> <dotted.key>` | The vendor has an update endpoint | Find it with DevTools' Network tab on their download page, filtered to XHR/Fetch. |
| `regex <url> <pattern>`   | Neither of the above              | One capture group. Brittle — vendors restyle pages.                               |

The directive is optional. Without it the package is still validated, just never
version-checked, and the checker warns once per run.

### 5. Wire it into a module

Declare it from whichever module owns the app, alongside that module's other package hooks:

```python
import os
from decman.plugins import aur

# decman reads `source.py` as text and `exec()`s it after `os.chdir`-ing into its
# directory, so package paths resolve relative to `nosarch/`, not to this file.
_PACKAGES_DIR: str = os.path.abspath("packages")


    @aur.custom_packages  # pyright: ignore[reportUnknownMemberType]
    def custom_pkgs(self) -> set[aur.CustomPackage]:
        return {
            aur.CustomPackage(
                pkgname="example-appimage",
                pkgbuild_directory=os.path.join(_PACKAGES_DIR, "example-appimage"),
            )
        }
```

decman prefers custom packages over AUR packages of the same name, so a name collision with
something in the AUR is harmless — the AUR entry is never fetched.

### 6. Check it

```sh
python3 tools/check_custom_packages.py --build
```

`--build` is slow but is the only way namcap can audit `depends`. Then review what the
package actually claims before trusting it:

```sh
pacman --query --list --file *.pkg.tar.zst
```

That listing is the real review step — it shows every path the package would install, so an
unexpected path stands out without reading any shell.

## The checker

`tools/check_custom_packages.py` covers both halves: whether each `pkgver` is behind
upstream, and whether the PKGBUILD itself is sound (structural checks, plus namcap when it
is installed).

It exits with a tiered status so a caller can distinguish "this will break the run" from
"this is merely stale":

| Code | Meaning                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------ |
| `0`  | Every package is valid and current.                                                                                            |
| `1`  | At least one package has an **error**: it does not parse, fails validation, or trips namcap. decman will fail to build it.     |
| `2`  | No errors, but at least one **warning**: behind upstream, no upstream declared, or the lookup failed. Everything still builds. |

Errors outrank warnings; a run with both exits `1`. `nosarch/source.py` runs it on every
decman invocation and aborts only on `1`.

Useful flags: `--offline` skips every network lookup, `--quiet` prints only packages with
something to report, and `--package NAME` narrows to one.

## Bumping a version

1. Run the checker; it names the packages that are behind and the version upstream is on.
2. Update `pkgver`, any `_commit`-style variable, and `sha256sums` (re-download, re-hash).
3. Reset `pkgrel` to `1`. Bump `pkgrel` instead of `pkgver` when only the recipe changed.
4. Re-run the checker with `--build`.

## Gotchas

These are real failures this repo has hit, not hypotheticals.

**Pin every remote source.** `SKIP` in `sha256sums` is legitimate only for files shipped
alongside the PKGBUILD. The checker treats `SKIP` on an `http(s)`/`git+` source as an error.

**`LicenseRef-` obliges you to ship the license.** A non-standard license identifier requires
the license text under `/usr/share/licenses/$pkgname/`, or namcap fails the package. Vendor
archives usually contain one — extract it in `prepare()` and install it in `package()`.

**Not every AppImage bundles a `.desktop` entry and icons.** Run `--appimage-extract` by hand
once and look before assuming they are there. When they are, install them from the extracted
tree rather than hand-maintaining copies; check that the entry's `Icon=` name matches the
icon files it ships, since vendors get this wrong.

**Expect namcap noise on repackaged binaries.** Unstripped ELFs, files outside FHS paths, and
missing hardening flags are properties of a binary we did not compile. The checker already
excludes those rules; do not "fix" them in the PKGBUILD.
