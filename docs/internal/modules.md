# Modules

Definition code is split into modules under `nosarch/modules/`. `nosarch/source.py` registers them.

## The modules

| Module        | Class                 | State name       | Enabled by                   | Sources                        |
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
| Apply         | `ApplyModule`         | `apply`          | always, registered last      | none                           |

The four setup modules live in `nosarch/modules/setups/`, the three packaging modules in
`nosarch/modules/packaging/`, and the rest are one file each in `nosarch/modules/`. `BasicSetupModule` is a setup that
predates the split, so it sits in `nosarch/modules/basic_setup.py` rather than in `setups/`.

`Enabled by` is the `enabled` yes/no setting on that section of the config classes in `nosarch/user_config.py`.
`config.schema.json` is generated from those classes. The module is enabled when that setting is true.

The `UserDefinedModule` (`nosarch/modules/user_defined.py`) installs packages the user listed in the config file, so
the engine does not remove them.

## Registration

`source.py` adds every module to the `Setup`, disabled ones included, with `enabled=` set from the config. A disabled
module is never asked for its declarations. It is there so its `on_disable` can run, as an ordinary method with the
module's own state, on the first run after it was turned off. A module deleted from the repository outright has no
`on_disable` left to run, so turn a module off for a run before deleting it.

The setups extend the desktop, so `source.py` stops if a setup is enabled without a module named `desktop`. Desktop is
currently always registered, so this never trips on a normal run — the guard is there for when NosArch allows headless
installs.

## Module names are state keys

`State name` above is the module's `name`. The files it deployed, its declarations from the last run, and the changes
its `on_change` has not seen yet are all recorded under it. Renaming a module makes every package and unit it declares
look newly added, so its `on_change` sees all of them.

## Registration order

Within a phase, hooks run in the order modules were added. The phases are listed on `engine.Module`.

`ApplyModule` must stay last. Its `after_update` runs the commands every other module requested in `on_change`, so a
module added below it would run its own `after_update` after those commands.
