# NosArch

NosArch is an Arch Linux dotfile and system configuration repo, deployed by its own engine.

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

`nosarch/apply.py` offers to log out or reboot at the end, for the changes that only take effect on a new login.
Everything that can be applied live is applied first. Declining the offer is fine: those changes apply the next time
you log out or reboot.

Switching from decman: run `nosarch/apply.py --import-decman` once, so the first run does not treat everything decman
deployed as new. The first full run then removes decman itself.
