# Packages

NosArch is responsible for managing packages on the system. The kinds of packages include:

- Arch and AUR,
- Homebrew (via NosArch's own `plugins/homebrew.py`, if enabled by user),
- Flatpak (system and per-user),
- and custom pacman packages ([Custom Packages](#custom-packages)).

## Declaring

Each plugin exposes decorators. A module method annotated with one returns the set (or dict, for user-scoped kinds) of
packages that module wants:

```python
@pacman.packages
def arch_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.arch"))

@aur.packages
def aur_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.aur"))

@flatpak.packages
def flatpak_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.flatpak"))

@flatpak.user_packages
def flatpak_user_pkgs(self) -> dict[str, set[str]]:
    return {self._username: set(self._user_config.get_str_list("user_packages.flatpak_user"))}

@homebrew.formulae
def brew_formulae(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.homebrew_formulae"))
```

## Tracking package changes

Decman provides the `Store` in `on_change` hooks from which package changes can be tracked. But the store only holds
the current run's entries per plugin, and a hook still has to know each plugin's store key and per-user shape to make
sense of it.

`utils/change_tracker.py`'s `ChangeTracker` makes tracking package changes easy. It snapshots every plugin's entries
in `before_update`, diffs them against what's there after, records which packages were added or removed on a run,
across every plugin (pacman, AUR, custom, flatpak, homebrew). It normalizes user-scoped kinds into a flat set of
names. `on_change` hooks only need `package_changed(...)` instead of reaching into the store itself.

```python
self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()
```

> - A module only needs one `ChangeTracker`, tracking both [files](files.md#tracking-file-changes) and package changes.
> - Each module should carry its own tracker so it sees only its own packages.

Then snapshot the store in `before_update` and diff in `on_change`:

```python
@override
def before_update(self, store: Store) -> None:
    self._tracker.snapshot_packages(store, self.name)

@override
def on_change(self, store: Store) -> None:
    self._tracker.diff_packages(store, self.name)

    if self._tracker.package_changed("mise", kinds=("pacman",)):
        ...

    if self._tracker.package_changed("visual-studio-code", kinds=("brew_cask",)):
        ...

    if self._tracker.package_changed(f"{self._username}:org.mozilla.firefox", kinds=("flatpak_user",)):
        ...
```

`self._tracker.added_pkgs` and `self._tracker.removed_pkgs` map each kind (`"pacman"`, `"aur"`, `"custom"`,
`"flatpak"`, `"flatpak_user"`, `"brew_formula"`, `"brew_cask"`, `"brew_tap"`) to a set of names. User-scoped kinds are
recorded as `"<user>:<pkg>"`. A module enabled for the first time sees everything as added.

`ChangeTracker` can also track `"systemd"` and `"systemd_user"` units.

## Custom Packages

For apps which do not have an Arch or Homebrew package, a custom package should be used. This custom package
implementation allows installing AppImages, vendor tarballs, or payloads behind `curl https://... | bash` installers.
Custom packages allows installing these as Arch packages that decman and pacman can manage.

### Why not the AUR

- **Security**: The PKGBUILD is managed by us. For a repackaged binary, we manage a URL and a checksum, which is
  easier to audit than an unfamiliar maintainer's build script. The checksum is a guarantee `curl | bash` cannot
  offer, since an install script fetches whatever is at the URL at the time.
- **Reliability**: Nothing resolves through the AUR, so a package cannot be orphaned or deleted out from under a run.

The cost is that we have to manage version bumps. `tools/check_custom_packages.py` checks for outdated versions and
find the latest version to bump to.

### Adding a custom package

A custom package is a PKGBUILD kept in this repo under `nosarch/packages/`.

#### 1. Create the directory

One directory per package under `nosarch/packages/`, named exactly as the `pkgname` it builds.

To avoid name collisions with packages from the AUR, suffix the name with `-nosarch`. So if there is a name collision,
AUR helpers would not assume it is an AUR package and try to update it themselves.

#### 2. Get the download URL and its checksum

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

#### 3. Write the PKGBUILD

Writing style:

- `# Maintainer: NosArch` as the first line, with the `# nosarch-upstream:` directive
  ([step 4](#4-declare-where-upstream-lives)) as the comment block right after it.
- Group the rest into two blocks, separated by a blank line:
    - Package info first, in this order: `pkgname`, `pkgdesc`, `pkgver`, `pkgrel`, `url`, `license`.
    - Build info second, in this order: `arch`, `depends`, `provides`, `conflicts` (if any), `options`, `source`,
      `sha256sums`.
- Then the functions, in this order, defining only the ones the package actually needs: `prepare()`, `build()`,
  `package()`.
- Always install the package's own `LICENSE`/similar file under `/usr/share/licenses/$pkgname/`, even when `license=`
  is a standard SPDX identifier and nothing forces it (see the `LicenseRef-` gotcha below for when it's mandatory).
- If the package offers shell completions, install them, but as best-effort. Guard the generation with `|| true` and
  only install a completion file if it came out non-empty A missing completion should never fail the build.

Match the existing custom package PKGBUILDs.

#### 4. Declare where upstream lives

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

##### Regex directive

> `regex` is fragile and should be a last resort. `json` and `text` point at an endpoint the vendor's own installer or
> updater reads to check for new versions, so it's a de facto stable contract. `regex` instead scrapes a page meant
> for a browser, not a scraper. A marketing copy update, a redesign, an A/B test, or a locale change can all move or
> reword the surrounding text without the vendor considering it a breaking change. Prefer other directives.
> Use `regex` only when a page is truly the only place the version is published.

The checker fetches `<url>` as plain text (the raw HTML, not rendered) and runs `<pattern>` against it as a Python
regex. Whatever the single capture group `(...)` matches is treated as the current upstream version.

Example: a vendor's download page contains `href="/dl/Example-2.4.1-x86_64.AppImage"`. The directive
`# nosarch-upstream: regex https://example.com/download 'Example-([0-9.]+)-x86_64'` matches that text and captures
`2.4.1`.

Keep exactly one capture group as the checker uses group 1 and ignores the rest of the match.

If the page renders its download links client-side (nothing but a JS bundle in the raw HTML), `regex` cannot see them.

#### 5. Wire it into a module

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

#### 6. Check it

```sh
python3 tools/check_custom_packages.py --build
```

pass `--build` so namcap can audit `depends` (slower process).

Then review what paths the package actually installs to, so an unexpected path stands out:

```sh
pacman --query --list --file *.pkg.tar.zst
```

### The checker

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

### Bumping a version

1. Run the checker; it names the packages that are behind and the version upstream is on.
2. Update `pkgver`, any `_commit`-style variable, and `sha256sums` (re-download, re-hash).
3. Reset `pkgrel` to `1`. Bump `pkgrel` instead of `pkgver` when only the recipe changed.
4. Re-run the checker with `--build`.

### Custom Package Gotchas

- **Pin every remote source**: `SKIP` in `sha256sums` is legitimate only for files shipped alongside the PKGBUILD.
  The checker treats `SKIP` on an `http(s)`/`git+` source as an error.
- **`LicenseRef-` obliges you to ship the license**: A non-standard license identifier requires the license text under
  `/usr/share/licenses/$pkgname/`, or namcap fails the package. Vendor archives usually contain one. Install it.
- **Not every AppImage bundles a `.desktop` entry and icons**: Run `--appimage-extract` by hand once and look before
  assuming they are there. Also check that the desktop entry's `Icon=` name matches the icon files it ships.
- **Expect namcap noise on repackaged binaries**: Unstripped ELFs, files outside FHS paths, and missing hardening
  flags are properties of a binary we did not compile. The checker already excludes those rules. Do not "fix" them in
  the PKGBUILD.
