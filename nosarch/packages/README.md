# Custom packages

PKGBUILDs for apps that ship no Arch package — AppImages, vendor tarballs, and the payloads
behind `curl | bash` installers. decman builds these in a clean chroot and hands the result
to pacman, exactly like an AUR package, except the recipe lives here and is reviewed by us.

**For the full workflow — creating a package, declaring its upstream, wiring it into a
module, checking it, and bumping versions — see `docs/internal/custom-packages.md`.**

This file is the PKGBUILD reference: what the fields mean, and a template to copy.

## Reading a PKGBUILD

A PKGBUILD is a shell script that `makepkg` sources. It sets some variables, then runs
functions with well-known names. For repackaging a prebuilt binary there is no compiling
involved — the whole file is "download this, verify it, copy these files to these paths."

### The variables

| Variable     | Meaning                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pkgname`    | What pacman calls the package. `pacman -R <pkgname>` removes it.                                                                                              |
| `pkgver`     | Upstream's version. Bumping it is what triggers a rebuild.                                                                                                    |
| `pkgrel`     | Bumped when the _recipe_ changes but the version does not. Reset to 1 on a `pkgver` bump.                                                                     |
| `_commit`    | Not special — any name starting with `_` is our own variable, invisible to makepkg. Used here to keep the download URL readable.                              |
| `arch`       | `('x86_64')` for a prebuilt x86 binary.                                                                                                                       |
| `depends`    | Runtime dependencies, as pacman package names. AppImages need `fuse2`.                                                                                        |
| `provides`   | Other names this package satisfies, so something depending on `cursor` is happy with `cursor-appimage`.                                                       |
| `conflicts`  | Packages that cannot be installed alongside this one. A convenience, not a safety net — pacman blocks file collisions regardless.                             |
| `options`    | `!strip` (do not try to strip a prebuilt binary), `!debug` (do not emit a debug package).                                                                     |
| `source`     | What to download. `name::url` saves the download under `name`.                                                                                                |
| `sha256sums` | One entry per `source`, same order. **This is the security control** — the build fails if the bytes do not match. `'SKIP'` disables the check for that entry. |

### The functions

Both are optional, and both run inside a throwaway build directory.

- **`prepare()`** — unpack and rearrange. For an AppImage, `--appimage-extract` unpacks it
  into `squashfs-root/` so we can pull the bundled `.desktop` entry and icons out.
- **`package()`** — copy the final files into `$pkgdir`, a fake empty root. Whatever path
  you create under `$pkgdir` is the path the file lands on at install time:
  `$pkgdir/usr/bin/cursor` becomes `/usr/bin/cursor`. That mapping is the only thing you
  really need to hold in your head.

### The two variables in the functions

- `$srcdir` — where downloaded and extracted sources are.
- `$pkgdir` — the fake root you are filling. Nothing outside it is ever touched.

### `install` instead of `cp`

`install -Dm755 SOURCE DEST` copies, creates missing parent directories (`-D`), and sets
permissions (`-m`) in one step. `755` for anything executable, `644` for data files like
`.desktop` entries and icons. `install -d DIR` just creates a directory.

## Template

For an AppImage. For a plain tarball, drop `prepare()` and copy out of the extracted
directory in `package()` instead.

```bash
pkgname=EXAMPLE-appimage
pkgver=0.0.0
pkgrel=1
pkgdesc="One line description"
arch=('x86_64')
url="https://example.com"
license=('LicenseRef-EXAMPLE-EULA')
depends=('fuse2' 'hicolor-icon-theme')
provides=('EXAMPLE')
options=('!strip' '!debug')
source=("$pkgname-$pkgver.AppImage::https://example.com/download/EXAMPLE-$pkgver-x86_64.AppImage")
sha256sums=('PASTE_SHA256_HERE')

prepare() {
    chmod +x "$srcdir/$pkgname-$pkgver.AppImage"
    "$srcdir/$pkgname-$pkgver.AppImage" --appimage-extract >/dev/null
}

package() {
    install -Dm755 "$srcdir/$pkgname-$pkgver.AppImage" "$pkgdir/opt/$pkgname/EXAMPLE.AppImage"

    install -d "$pkgdir/usr/bin"
    ln -s "/opt/$pkgname/EXAMPLE.AppImage" "$pkgdir/usr/bin/EXAMPLE"

    install -Dm644 "$srcdir/squashfs-root/EXAMPLE.desktop" \
        "$pkgdir/usr/share/applications/EXAMPLE.desktop"

    local icon size
    for icon in "$srcdir"/squashfs-root/usr/share/icons/hicolor/*/apps/EXAMPLE.png; do
        size="$(basename "$(dirname "$(dirname "$icon")")")"
        install -Dm644 "$icon" "$pkgdir/usr/share/icons/hicolor/$size/apps/EXAMPLE.png"
    done
}
```

Not every AppImage bundles a `.desktop` entry and icons. Run `--appimage-extract` once by
hand and look at what is inside before assuming the loop above will find anything.
