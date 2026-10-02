# Modules

Definition code is split into modules under `nosarch/modules/`. `nosarch/source.py` registers them.

## The modules

| Module        | Class               | Enabled by          | Sources                  |
| ------------- | ------------------- | ------------------- | ------------------------ |
| System        | `SystemModule`      | always              | `dotfiles/system-root`   |
| Desktop       | `DesktopModule`     | always              | `dotfiles/desktop-root`  |
| Theming       | `ThemingModule`     | always              | `nosarch/themes/`        |
| Setup         | `SetupModule`       | `profiles.setup`    | `dotfiles/setup-root`    |
| AI            | `AIModule`          | `profiles.ai`       | `dotfiles/ai-root`       |
| Creative      | `CreativeModule`    | `profiles.creative` | `dotfiles/creative-root` |
| Dev           | `DevModule`         | `profiles.dev`      | `dotfiles/dev-root`      |
| Gaming        | `GamingModule`      | `profiles.gaming`   | `dotfiles/gaming-root`   |
| Homebrew      | `HomebrewModule`    | `enable_homebrew`   | generated at run time    |
| User packages | `UserDefinedModule` | always              | none                     |

AI, Creative, Dev, and Gaming live in `nosarch/modules/usage_profiles/`. The others are one file each in `nosarch/modules/`.

`Enabled by` is the key in `config.schema.json`. The module is registered when that key is true.

The `UserDefinedModule` (`nosarch/modules/user_defined.py`) is for managing packages defined by the user in the config
file. This allows users to install packages not defined in the definition code and not worry about them being removed
by decman.

## Registration

System, Desktop, Theming, and User packages are always registered.

Setup, AI, Creative, Dev, and Gaming register only when their `profiles.*` key is true. They extend the desktop, so
`source.py` exits if no registered module is named `desktop`. Desktop is currently always registered, so that exit
does not happen on a normal run. This guard is in place for when NosArch allows headless installs.

## Module names are store keys

A module's `name` is its key in decman's store. Per-module package, unit, and flatpak entries, the `enabled_modules`
list, and `ChangeTracker` diffs all use it. Renaming a module leaves the old entries in place. On the next run,
`ChangeTracker` treats everything that module declares as newly added.
