# Custom Packages

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

Writing style:

- `# Maintainer: NosArch` as the first line, with the `# nosarch-upstream:` directive
  ([step 4](#4-declare-where-upstream-lives)) as the comment block right after it.
- Group the rest into two blocks, separated by a blank line:
    - Package info first, in this order: `pkgname`, `pkgdesc`, `pkgver`, `pkgrel`, `url`, `license`.
    - Build info second, in this order: `arch`, `depends`, `provides`, `conflicts` (if any), `options`, `source`,
      `sha256sums`.
- Then the functions, in this order, as needed: `prepare()`, `build()`, `package()`.
- Always install the package's own `LICENSE`/similar file under `/usr/share/licenses/$pkgname/`, even when `license=`
  is a standard SPDX identifier and nothing forces it.
- If the package offers shell completions, install them, but as best-effort. Guard the generation with `|| true` and
  only install a completion file if it came out non-empty A missing completion should never fail the build.

Match the existing custom package PKGBUILDs.

### 4. Declare where upstream lives

Add one directive comment near the top of the PKGBUILD so the checker can tell when the package version is old:

```bash
# nosarch-upstream: github <owner>/<repo>
# nosarch-upstream: json https://example.com/api/latest version
# nosarch-upstream: text https://example.com/stable
# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'
```

| Form                      | Use when                                   | Notes                                                                                       |
| ------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `github <owner>/<repo>`   | The app has GitHub releases                | Reads `tag_name`, strips a leading `v`.                                                     |
| `json <url> <dotted.key>` | The vendor has an update endpoint          | Find it with Browser DevTools' Network tab on their download page, filtered to XHR/Fetch.   |
| `text <url>`              | The vendor publishes a bare version string | The body is the version (what the vendor's own installer reads). First line; no parsing.    |
| `regex <url> <pattern>`   | Neither of the above                       | One capture group. Fragile as vendors restyle pages. Prefer other directives when possible. |

The directive is optional. Without it the package is not version-checked.

#### Regex directive

> `regex` is fragile and should be a last resort. `json` and `text` point at an endpoint the vendor's own installer or
> updater reads to check for new versions, so it's much more stable. `regex` scrapes a page meant for a browser. Any
> update to the page text or content can move or reword the surrounding text without it being a breaking change.
> Prefer other directives. Use `regex` only when a page is truly the only place the version is published.

The checker fetches `<url>` as plain text (the raw HTML) and runs `<pattern>` against it as a Python regex. Whatever
the single capture group `(...)` matches is treated as the current upstream version.

Example: a vendor's download page contains `href="/dl/Example-2.4.1-x86_64.AppImage"`. The directive
`# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'` matches that text and captures
`2.4.1`.

Keep exactly one capture group as the checker uses group 1 and ignores the rest of the match.

### 5. Wire it into a module

Declare it in the definition code. Example:

```python
import os
from decman.plugins import aur

# decman reads `source.py` as text and `exec()`s it after `os.chdir` into its dir, so paths are relative to `nosarch/`.
_PACKAGES_DIR: str = os.path.abspath("packages")

    @aur.custom_packages
    def custom_pkgs(self) -> set[aur.CustomPackage]:
        return {
            aur.CustomPackage(
                pkgname="package-nosarch", pkgbuild_directory=os.path.join(_PACKAGES_DIR, "package-nosarch"),
            )
        }
```

### 6. Test it

1. Verify the PKGBUILD is valid: `python3 tools/check_custom_packages.py --package <package-name>`
    - Pass `--build` so namcap can audit `depends` (slower process).
2. Check that the package actually installs to only the intended paths: `pacman --query --list --file *.pkg.tar.zst`

## The checker

`tools/check_custom_packages.py` checks whether each package is outdated, and whether the PKGBUILD itself is valid and
builds successfully.

The checker exits with the following codes:

| Exit Code | Meaning                                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------------------------- |
| `0`       | Every package is valid and current.                                                                                 |
| `1`       | At least one **error**: PKGBUILD does not parse, fails validation, or trips namcap. Builds will fail.               |
| `2`       | At least one **warning**: package is outdated, no upstream is declared, or the lookup failed. Builds still succeed. |

Errors outrank warnings, so a run with both exits `1`.

## Version Upgrades

If the package has self-updating, blocking self-updates should be implemented as best-effort.

To upgrade PKGBUILDs of custom packages:

1. Run `python3 tools/check_custom_packages.py` to see which packages are behind.
2. Set `pkgver` to that version and reset `pkgrel=1`.
3. Update any other variable the `source=()` URLs depend on (per-directive, see below).
4. Refresh the checksums from inside the package directory:

    ```sh
    cd nosarch/packages/<pkgname>
    updpkgsums   # from pacman-contrib: downloads every source and rewrites sha256sums
    ```

5. Run `python3 tools/check_custom_packages.py --package <pkgname> --build` to make sure it still builds and passes
   namcap audit.
6. Read `git diff`. Only `pkgver`, `pkgrel`, the hashes, and whatever was changed in step 3 should have moved.

Step 3 differs between upstream directives:

### GitHub Releases

Release assets almost always live at `https://github.com/<owner>/<repo>/releases/download/v$pkgver/<asset>`, so the
version is the only moving part. Steps 1, 2, 4 and 5 are all there is.

### `json`

The endpoint usually returns more than the version, and the download URL often contains something besides it (a build
hash, a CDN path, a build number). Fetch the endpoint and compare its URL with the one in `source=()`:

```sh
curl --silent "<endpoint-url>" | python3 -m json.tool
```

Everything in the returned URL that is not the version has to be copied into the PKGBUILD as well.

Example, Cursor (`cursor-nosarch`). The endpoint returns:

```json
{
    "downloadUrl": "https://downloads.cursor.com/production/37076c6c.../linux/x64/Cursor-3.22.7-x86_64.AppImage",
    "version": "3.22.7",
    "commitSha": "37076c6c..."
}
```

The URL embeds the commit hash, so a bump sets both `pkgver=3.22.7` and `_commit=<commitSha>`. Changing only `pkgver`
builds `.../production/<old commit>/.../Cursor-3.22.7-...`, which does not exist, and the download fails.

After editing, check that the URL makepkg will build matches `downloadUrl` exactly:

```sh
cd nosarch/packages/cursor-nosarch
makepkg --printsrcinfo | grep source
```

### `text`

The endpoint returns only the version, so nothing tells you whether the URL format is still the same. Read the vendor's
installer script to see how it builds the download URL from that version:

```sh
curl --location "<installer-url>" | less
```

If the URL pattern in the script matches the PKGBUILD's `source=()`, this is as easy as `github`. If the script has
changed (a new host, a new file name, a new architecture suffix, a new extra file), update `source=()` to match before
running `updpkgsums`. Only re-read the script on bumps where `updpkgsums` fails or the version jumped a major number.

Example, Grok Build (`grok-build-nosarch`). `https://x.ai/cli/stable` returns `1.0.41`, and the binary lives at
`https://x.ai/cli/grok-$pkgver-linux-x86_64`, so a bump is just `pkgver`.

Watch for sources that don't include the version. Grok's `LICENSE` is fetched from the `main` branch, so its hash can
change between two bumps, or with no bump at all. When `updpkgsums` changes a hash for a file whose URL did not change,
look at what changed in the file before accepting it.

### `regex`

The regex gives you a version, but nothing about the URL. Open the page the directive scrapes and check that the
download link still has the shape `source=()` expects.

If the checker reports the lookup failed (exit `2`, "lookup failed") instead of a version, the page changed and the
pattern no longer matches. Fix the pattern first: open the raw HTML (`curl --location "<url>" | less`), find the new
text around the version, and update the directive. Then bump as usual.

## Custom Package Gotchas

- **Pin every remote source**: `SKIP` in `sha256sums` is legitimate only for files shipped alongside the PKGBUILD.
  The checker treats `SKIP` on an `http(s)`/`git+` source as an error.
- **`LicenseRef-` obliges you to ship the license**: A non-standard license identifier requires the license text under
  `/usr/share/licenses/$pkgname/`, or namcap fails the package. Vendor archives usually contain one. Install it.
- **Not every AppImage bundles a `.desktop` entry and icons**: Run `--appimage-extract` by hand once and look before
  assuming they are there. Also check that the desktop entry's `Icon=` name matches the icon files it ships.
- **A vendor that ships no license gets a pointer note, not a scraped license**: the "always ship a LICENSE" rule
  presumes upstream published one. When it has not, and the only thing it publishes are service terms (a ToS page),
  do not scrape the page to fake a license file: the bytes churn on restyles and the build fails for no reason.
  Declare `LicenseRef-<something>` (namcap rejects `custom`) and install a short README under
  `/usr/share/licenses/$pkgname/` that records the status and links the terms, stating it is not a license.
  `devin-cli-nosarch` is the current example; its PKGBUILD records the reasoning.
- **Expect namcap noise on repackaged binaries**: Unstripped ELFs, files outside FHS paths, and missing hardening
  flags are properties of a binary we did not compile. The checker already excludes those rules. Do not "fix" them in
  the PKGBUILD.
