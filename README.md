# NosArch

Arch Linux setup inspired by [Omarchy](https://github.com/basecamp/omarchy).

Managed using [Decman](https://github.com/kiviktnm/decman)

---

## Usage

1. Install Decman (https://github.com/kiviktnm/decman#installation)
2. Clone this repository: `git clone https://github.com/abdulk-id/NosArch ~/NosArch`
3. Configure NosArch in `~/NosArch/nosarch/config.json`. Use [`config.schema.json`](config.schema.json) for validating the config JSON.
4. Run decman: `sudo decman --source ~/NosArch/nosarch/source.py`
    - Dry-run decman to see what changes will be made without applying them: `sudo decman --source ~/NosArch/nosarch/source.py --dry-run`

---

## Notes

- Currently for single-user setups only. Multi-user setups later.
- [Quickshell](https://git.outfoxxed.me/quickshell/quickshell) coming later.
