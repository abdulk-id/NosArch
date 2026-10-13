# Modules

Definition code is split into modules under `nosarch/modules/`. `nosarch/source.py` registers them.

## The modules

| Module        | Class                 | Store name       | Enabled by                   | Sources                        |
| ------------- | --------------------- | ---------------- | ---------------------------- | ------------------------------ |
| System        | `SystemModule`        | `system`         | always                       | `dotfiles/system-root`         |
| Desktop       | `DesktopModule`       | `desktop`        | always                       | `dotfiles/desktop-root`        |
| Theming       | `ThemingModule`       | `theming`        | always                       | `nosarch/themes/`              |
| Basic setup   | `BasicSetupModule`    | `basic_setup`    | `setups.basic.enabled`       | `dotfiles/basic-setup-root`    |
| AI            | `AISetupModule`       | `ai_setup`       | `setups.ai.enabled`          | `dotfiles/ai-setup-root`       |
| Creative      | `CreativeSetupModule` | `creative_setup` | `setups.creative.enabled`    | `dotfiles/creative-setup-root` |
| Dev           | `DevSetupModule`      | `dev_setup`      | `setups.dev.enabled`         | `dotfiles/dev-setup-root`      |
| Gaming        | `GamingSetupModule`   | `gaming_setup`   | `setups.gaming.enabled`      | `dotfiles/gaming-setup-root`   |
| Homebrew      | `HomebrewModule`      | `homebrew`       | `packaging.homebrew.enabled` | `dotfiles/system-root`         |
| Flatpak       | `FlatpakModule`       | `flatpak`        | `packaging.flatpak.enabled`  | `dotfiles/system-root`         |
| Snap          | `SnapModule`          | `snap`           | `packaging.snap.enabled`     | `dotfiles/system-root`         |
| User packages | `UserDefinedModule`   | `user_defined`   | always                       | none                           |

The four setup modules live in `nosarch/modules/setups/`, the three packaging modules in
`nosarch/modules/packaging/`, and the rest are one file each in `nosarch/modules/`. `BasicSetupModule` is a setup that
predates the split, so it sits in `nosarch/modules/basic_setup.py` rather than in `setups/`.

`Enabled by` is the key in `config.schema.json`, and it is the `enabled` boolean inside that section rather than the
section itself. The module is registered when that key is true.

The `UserDefinedModule` (`nosarch/modules/user_defined.py`) installs packages the user listed in the config file, so
decman does not remove them.

## Registration

System, Desktop, Theming, and User packages are always registered. The others register when their `setups.*` or
`packaging.*` key is true. They extend the desktop, so `source.py` exits if no registered module is named
`desktop`. Desktop is currently always registered, so this never trips on a normal run — the guard is there for when
NosArch allows headless installs.

## Module names are store keys

`Store name` above is the module's decman `name`. Per-module package, unit, and flatpak entries, the `enabled_modules`
list, and `ChangeTracker` diffs all use it. Renaming a module leaves the old entries in place, and on the next run
`ChangeTracker` treats everything that module declares as newly added.
