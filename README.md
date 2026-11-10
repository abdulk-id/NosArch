# NosArch

NosArch is an Arch Linux dotfile and system configuration repo, deployed by its own engine.

> **The documentation in `docs/` is outdated.** It has not been revised since the engine replaced decman, so parts of it
> describe things that no longer exist, such as decman, its parity tests and `--import-decman`. Trust the code over the
> docs until they have been reviewed.

## Usage

1. Install `git` and `python`.
2. Clone this repository:

    ```sh
    git clone https://github.com/abdulk-id/NosArch ~/NosArch
    ```

3. Configure NosArch in `~/.nosarch_config.json`. Use [`config.schema.json`](config.schema.json) for validating the config JSON.
4. Apply the configuration:

    ```sh
    ~/NosArch/nosarch/apply.py
    ```

    Or, from the repository, `mise run apply`. It asks for your password with sudo.

    To see what changes would be made without applying them, which needs no root:

    ```sh
    ~/NosArch/nosarch/apply.py --dry-run
    ```
