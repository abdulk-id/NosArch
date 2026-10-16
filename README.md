# NosArch

NosArch is a single-user Arch-based Linux system.

## Usage

1. Install Decman (https://github.com/kiviktnm/decman#installation)
2. Clone this repository:

    ```sh
    git clone https://github.com/abdulk-id/NosArch ~/NosArch
    ```

3. Configure NosArch in `~/.nosarch_config.json`. Use [`config.schema.json`](config.schema.json) for validating the config JSON.
4. Run decman:

    ```sh
    sudo decman --source ~/NosArch/nosarch/source.py
    ```

    To see what changes decman will make without applying them, run a dry run:

    ```sh
    sudo decman --source ~/NosArch/nosarch/source.py --dry-run
    ```
