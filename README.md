# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by [Decman](https://github.com/kiviktnm/decman).

## Usage

1. Install Decman (https://github.com/kiviktnm/decman#installation)
2. Clone this repository:

    ```sh
    git clone https://github.com/abdulk-id/NosArch ~/NosArch
    ```

3. Configure NosArch in `~/.nosarch_config.json`. Use [`config.schema.json`](config.schema.json) for validating the config JSON.
4. Apply the configuration:

    ```sh
    sudo ~/NosArch/tools/apply --source ~/NosArch/nosarch/source.py
    ```

    Or, from the repository, `mise run apply`.

    To see what changes would be made without applying them:

    ```sh
    sudo ~/NosArch/tools/apply --source ~/NosArch/nosarch/source.py --dry-run
    ```

`tools/apply` runs decman and then offers to log out or reboot, for the changes that only take effect on a new login.
Everything that can be applied live is applied first. Declining the offer is fine: those changes apply the next time
you log out or reboot. Running `decman` directly applies them the same way; it just does not offer the action.
