# Dotfiles

A dotfile is any file NosArch applies to the target system. Most live under `nosarch/dotfiles/`, in a mirrored root
per module or group of modules. Hidden names are stored with a `dot_` prefix, which
[`UserhomeDotfiles`](../../nosarch/utils/paths.py) handles. Theming applies wallpapers from
`nosarch/definition/themes/` instead. `nosarch/dotfiles/unused/` holds material that is not applied, kept until it is
either used or dropped.

## Every file is declared individually

[`Directory()`](../../nosarch/engine/fs.py) applies a whole source tree. Definition code names files explicitly.
`ThemingModule` is the exception: each theme's wallpapers are not a fixed set.

- Reading a module lists every path it applies. A directory declaration does not.
- A `Directory()` ships whatever is in the tree, including an editor backup, the moment it is saved. An undeclared
  file under `nosarch/dotfiles/` is inert.
- `Directory` applies one owner, mode, and `bin_files` to every file it walks. The Plymouth theme mixes PNGs with text
  that needs substitution, and one declaration cannot do both.

[`File.render`](../../nosarch/engine/fs.py) copies bytes when a module sets no variables, or when `bin_file` is set.
One variable decodes every other text file in that module, so its binaries opt out.
[`file_variables()`](../../nosarch/engine/steps/files.py) is read when the files step runs, after every
`before_update`, so a value can depend on a hook. Hooks do not run on a dry run.

A change to a dotfile reaches the running system through `on_change`; see [hooks.md](hooks.md#applying-a-change).
