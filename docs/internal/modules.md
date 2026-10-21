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

`Enabled by` is the `enabled` yes/no setting on that section of the config classes in `nosarch/user_config.py`.
`config.schema.json` is generated from those classes. The module is registered when that setting is true.

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

## Registration order carries no behaviour

Nothing may depend on a module being registered first or last. decman runs the hooks in phases, and the phases, not the
order, are what a hook may rely on:

1. **`before_update`**, for every module (`app.py:278`).
2. The execution steps: files, then the plugins (`source.py`).
3. **`on_change`**, for changed modules only (`app.py:338`).
4. **`after_update`**, for every module (`app.py:347`).
5. The store is written, in `__exit__`, after every hook (`app.py:77`, `core/store.py:49`). The process then exits.

Two consequences:

- All `on_change` hooks finish before any `after_update` hook starts (`app.py:231-234`), so a change one module records is
  visible to anything running later in the same run.
- **The last thing decman does is save its store**, which is why the offer to log out or reboot belongs to `tools/apply`
  rather than to a hook. See [Prompting ends the run](files.md#prompting-ends-the-run).

A prompt placed in the last module's `after_update` would work, and would break silently the day someone registers a
module after it. That is the trade this avoids.
