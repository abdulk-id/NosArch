# NosArch

NosArch is an Arch Linux dotfile and system configuration repo, applied by its own engine.

See [docs/](docs/README.md) for the project overview, internal design notes, and maintainer procedures.

## Usage

1. Install `git` and `python`.
2. Clone this repository:

    ```sh
    git clone https://github.com/abdulk-id/NosArch ~/NosArch
    ```

3. Configure NosArch in `~/.nosarch_config.json`. Use [`config.schema.json`](config.schema.json) for validating the
   config JSON.
4. From `~/NosArch`, apply the configuration:

    ```sh
    python -m nosarch  # re-runs itself with sudo
    ```

    To see what changes would be made without applying them:

    ```sh
    python -m nosarch --dry-run
    ```
