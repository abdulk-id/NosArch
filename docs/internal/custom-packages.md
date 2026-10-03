# Custom Packages

Custom packages allows installing any app as a pacman package. This allows decman to manage the app.
This is useful for AppImages, `curl https://... | bash` installers, and vendor tarballs.

Custom packages are defined by a PKGBUILD placed in `nosarch/packages/<pkgname>`.

## Why not the AUR

- **Security**: The PKGBUILD is managed by us. For repackaged binaries, we manage a URL and a checksum. The checksum
  is a guarantee `curl | bash` cannot offer, since an install script fetches whatever is at the URL at the time.
- **Reliability**: Nothing resolves through the AUR, so a package cannot be orphaned or deleted out from under a run.

The cost is that we have to manage version bumps. `tools/check_custom_packages.py` checks for outdated versions.

## Upstream Directives

Upstream directives tell the checker how to find the current version of the app.

Add one `# nosarch-upstream:` directive near the top of the PKGBUILD so the checker can tell when the package
version is old:

```bash
# nosarch-upstream: github <owner>/<repo>
# nosarch-upstream: json https://example.com/api/latest version
# nosarch-upstream: text https://example.com/stable
# nosarch-upstream: regex https://example.com/download Example-([0-9.]+)-x86_64
```

| Name            | Form                      | Use when                                   |
| --------------- | ------------------------- | ------------------------------------------ |
| GitHub Releases | `github <owner>/<repo>`   | The app has GitHub releases                |
| JSON Endpoint   | `json <url> <dotted.key>` | The vendor has an update endpoint          |
| Raw Text        | `text <url>`              | The vendor publishes a bare version string |
| Regex           | `regex <url> <pattern>`   | Neither of the above                       |

The directive is optional. Without it the package is not version-checked.

### Regex directive

> `regex` is fragile and should be a last resort. `json` and `text` point at an endpoint the vendor's own installer
> or updater reads, so they are much more stable. `regex` scrapes a page meant for a browser, and any restyle can
> move or reword the surrounding text. Use `regex` only when a page is truly the only place the version is published.

The checker fetches `<url>` as plain text (the raw HTML) and runs `<pattern>` against it as a Python regex.
Whatever the single capture group `(...)` matches is treated as the current upstream version. Keep exactly one
capture group — the checker uses group 1 and ignores the rest.

Example: a vendor's download page contains `href="/dl/Example-2.4.1-x86_64.AppImage"`. The directive
`# nosarch-upstream: regex https://example.com/download Example-([0-9.]+)-x86_64` matches that text and captures
`2.4.1`.

### What a bump changes (per directive)

Bumping a version is not always just `pkgver` — what else in the PKGBUILD has to move depends on the directive:

#### GitHub Releases

Release assets are at `https://github.com/<owner>/<repo>/releases/download/v$pkgver/<asset>`, so only `pkgver` changes.

#### JSON Endpoint

The endpoint usually returns more than the version, and the download URL may contain something besides it (a build
hash, a CDN path, a build number). Fetch the endpoint and compare its URL with the one in `source=()`:

```sh
curl --silent "<endpoint-url>" | python3 -m json.tool
```

Everything in the returned URL that is not the version has to be copied into the PKGBUILD as well.

> Example: Cursor (`cursor-desktop-nosarch`). Its endpoint returns:
>
> ```json
> {
>     "debUrl": "https://downloads.cursor.com/production/37076c6c.../linux/x64/deb/amd64/deb/cursor_3.22.7_amd64.deb",
>     "version": "3.22.7",
>     "commitSha": "37076c6c..."
> }
> ```
>
> The URL embeds the commit hash, so a bump sets `pkgver=3.22.7` and `_commit=<commitSha>`. Changing only `pkgver`
> builds `.../production/<old commit>/.../cursor_3.22.7_amd64.deb`, which doesn't exist, and the download fails.
>
> After editing, check that the URL makepkg will build matches `debUrl` exactly:
>
> ```sh
> cd nosarch/packages/cursor-desktop-nosarch
> makepkg --printsrcinfo | grep source
> ```

#### Raw Text

The endpoint returns only the version, so nothing tells you whether the URL format is still the same. Read the
vendor's installer script to see how it builds the download URL from that version:

```sh
curl --location "<installer-url>" | less
```

If the URL pattern in the script matches the PKGBUILD's `source=()`, this is as easy as `github`. If the script has
changed (a new host, a new file name, a new architecture suffix, a new extra file), update `source=()` to match
before running `updpkgsums`. Only re-read the script on bumps where `updpkgsums` fails or the version jumped a
major number.

> Example: Grok Build (`grok-build-nosarch`). `https://x.ai/cli/stable` returns `1.0.41`, and the binary lives at
> `https://x.ai/cli/grok-$pkgver-linux-x86_64`, so a bump is just `pkgver`.

Watch for sources that don't include the version.

> Example: Grok Build's `LICENSE` is fetched from the `main` branch, so its hash can change between two bumps, or
> with no bump at all.

When `updpkgsums` changes a hash for a file whose URL did not change, look at what changed in the file.

#### Regex

The regex gives you a version, but nothing about the URL. Open the page the directive scrapes and check that the
download link still has the shape `source=()` expects.

If the checker reports the lookup failed (exit `2`, "lookup failed") instead of a version, the page changed and the
pattern no longer matches. Fix the pattern first: open the raw HTML (`curl --location "<url>" | less`), find the new
text around the version, and update the directive. Then bump as usual.

## Adding a custom package

### 1. Create the directory

A directory per package under `nosarch/packages/`, named exactly as the `pkgname` it builds.

Suffix the name with `-nosarch` to avoid collisions with AUR packages. Otherwise a name collision would make AUR
helpers replace the custom package with the package from the AUR.

### 2. Get the download URL and its checksum

Find the actual files `package()` needs to fetch, and pin each with a checksum.

- **AppImage or tarball**: the download URL is the artifact itself.

    ```sh
    curl --location --output example.AppImage "<url>"
    sha256sum example.AppImage
    ```

- **`curl https://... | bash` installer**: Read the installer script to find the URL(s) it fetches (a `.deb`, tarball,
  or binary), and pin those. If the script builds the URL from a version string, that version is what
  [upstream directive](#upstream-directives) needs to track.

    ```sh
    curl --location "<installer-url>" | less   # read it, don't run it
    curl --location --output example.tar.gz "<real-payload-url-found-in-script>"
    sha256sum example.tar.gz
    ```

Pin every hash so if the bytes at a pinned URL change, the build fails instead of installing something unexpected.

### 3. Write the PKGBUILD

Writing style:

- `# Maintainer: NosArch` as the first line, with the `# nosarch-upstream:` directive
  ([Upstream Directives](#upstream-directives)) as the comment block right after it.
- Group the rest into two blocks, separated by a blank line:
    - Package info first, in this order: `pkgname`, `pkgdesc`, `pkgver`, `pkgrel`, `url`, `license`.
    - Build info second, in this order: `arch`, `depends`, `provides`, `conflicts`, `options`, `source`, `sha256sums`.
- Then the functions, in this order, as needed: `prepare()`, `build()`, `package()`.
- Always install the package's `LICENSE`/similar file under `/usr/share/licenses/$pkgname/`, even when `license=` is a
  standard SPDX identifier.
- Always install shell completions if the package offers them. Guard the generation with `|| true` and only install a
  completion file if it came out non-empty. Missing completions should not fail the build.

Match the existing custom package PKGBUILDs.

Only add comments to explain non-standard behavior, and keep them concise. Obvious commands and behavior already
documented does not need comments (For example, if there are no shell completions, no need to comment saying so).

### 4. Declare where upstream lives

Add the `# nosarch-upstream:` directive described in [Upstream Directives](#upstream-directives).

### 5. Test it

1. Verify the PKGBUILD is valid: `python3 tools/check_custom_packages.py --package <package-name>`
    - Pass `--build` so namcap can audit `depends` (slower process).
2. Check that the package actually installs to only the intended paths: `pacman --query --list --file *.pkg.tar.zst`

### 6. Wire it into a module

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

If the package self-updates on its own, block that as best-effort.

A common approach to block self-updates of CLI packages is to add a thin wrapper script that blocks `update` and
`uninstall` commands with a message that it is being managed by a pacman package.

To upgrade PKGBUILDs of custom packages:

1. Run `python3 tools/check_custom_packages.py` to see which packages are behind.
2. Set `pkgver` to that version and reset `pkgrel=1`.
3. Update any other variable the `source=()` URLs depend on (see [What a bump changes](#what-a-bump-changes-per-directive)).
4. Refresh the checksums from inside the package directory: `cd nosarch/packages/<pkgname> && updpkgsums`.
5. Run `python3 tools/check_custom_packages.py --package <pkgname> --build` to make sure it still builds and passes
   namcap audit.

Only `pkgver`, `pkgrel`, the hashes, and whatever was changed in step 3 should have moved.

## Custom Package Gotchas

- **Pin every remote source**: `SKIP` checksum is only for files shipped alongside the PKGBUILD. The checker treats
  `SKIP` on an `http(s)`/`git+` source as an error.
- **namcap requires installing non-standard (`LicenseRef-`) licenses**.
- **Not every AppImage bundles a `.desktop` entry and icons**: Run `--appimage-extract` and check.
- **Add a note when no license is found**: When no license is published upstream, declare `LicenseRef-<something>`
  (namcap rejects `custom`) and install a short README that records the status.
    - Example: `devin-cli-nosarch`.
- **Expect namcap noise on repackaged binaries**: Unstripped ELFs, files outside FHS paths, and missing hardening
  flags are properties of a binary we did not compile. The checker already excludes those rules. Do not "fix" them.
- **An executable whose name ends in `.desktop` breaks `uwsm` launches**: `uwsm app` treats any argument ending in
  `.desktop` as a desktop entry file, so a launcher that passes the entry's `Exec` line verbatim makes uwsm parse the
  ELF as a `.desktop` file and fail. Point the installed desktop entries at a suffix-free `/usr/bin` symlink instead.
    - Example: `opencode-desktop-nosarch`. Upstream names the binary `ai.opencode.desktop`.
