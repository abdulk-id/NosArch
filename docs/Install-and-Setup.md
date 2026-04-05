# My Arch Linux Setup

## Installation

- Connect to WiFi: `wifi-menu -o`
- Ensure that the system clock is accurate: `timedatectl set-ntp true`
- List all disks to check drive name: `fdisk -l`
- Select disk for partitioning (example disk name: '/dev/nvme0n1'): `fdisk /dev/nvme0n1`
- Enter these commands for setting up disk partitions:
  - `g` - Create a new GPT partition table
  - `n` - Create a new partition
  - `1` - Number the new partition 1
  - Press enter - Set the first sector to default
  - `+2G` - Set size of first partition to 2 GB
  - `t` - Change partition type (since only one partition exists, it auto selects that partition. If not, then press `1` to select the partition we just made).
  - `1` - Set partition type to `EFI System`
  - `n` - Create a new partition
  - `2` - Number the new partition 2
  - Press enter - Set the first sector to default
  - Press enter - Use the rest of the disk for second partition
  - `w` - Write changes
- Format the boot partition: `mkfs.vfat -F 32 /dev/nvme0n1p1`
- Encrypt the second partition: `cryptsetup luksFormat /dev/nvme0n1p2`
  - Set the disk password.
- Open the second partition: `cryptsetup open /dev/nvme0n1p2 cryptroot`
  - This creates `/dev/mapper/cryptroot`
- Format the second partition as Btrfs: `mkfs.btrfs /dev/mapper/cryptroot`
- Mount the filesystem:
  - Mount the Btrfs partition: `mount /dev/mapper/cryptroot /mnt`
  - Make the mount point for the boot partition: `mkdir /mnt/boot`
  - Mount the boot partition: `mount /dev/nvme0n1p1 /mnt/boot`
- Create the Btrfs subvolumes:
  - `btrfs subvolume create /mnt/@`
  - `btrfs subvolume create /mnt/@home`
  - `btrfs subvolume create /mnt/@log`
  - `btrfs subvolume create /mnt/@pkg`
  - `btrfs subvolume create /mnt/@swap`
- Unmount everything: `umount /mnt`
- Mount everything properly:
  - The main subvolume: `mount -o noatime,compress=zstd:3,space_cache=v2,subvol=@ /dev/mapper/cryptroot /mnt`
  - Create the mount points: `mkdir -p /mnt/{home,var/log,var/cache/pacman/pkg,.swap}` & `mkdir /mnt/boot`
  - The home subvolume: `mount -o noatime,compress=zstd:3,space_cache=v2,subvol=@home /dev/mapper/cryptroot /mnt/home`
  - The log subvolume: `mount -o noatime,compress=zstd:3,space_cache=v2,subvol=@log /dev/mapper/cryptroot /mnt/var/log`
  - The pkg cache subvolume: `mount -o noatime,compress=zstd:3,space_cache=v2,subvol=@pkg /dev/mapper/cryptroot /mnt/var/cache/pacman/pkg`
  - The swap subvolume: `mount -o noatime,subvol=@swap /dev/mapper/cryptroot /mnt/.swap`
  - The boot partition: `mount /dev/nvme0n1p1 /mnt/boot`
- Install packages needed to "bootstrap" the system: `pacstrap -K /mnt base base-devel linux linux-headers linux-lts linux-lts-headers linux-firmware intel-ucode efibootmgr limine networkmanager btrfs-progs zram-generator cryptsetup snapper sudo man vim nano`
  - Packages installed:
    - `apparmor` - Application Sandboxing
    - `base` - Minimal package set to define a basic Arch Linux installation
    - `base-devel` - Basic tools to build Arch Linux packages
    - `linux` - The Vanilla Linux Kernel
    - `linux-headers` -
    - `linux-lts` - The Long-term support Linux Kernel (installed as a fallback kernel)
    - `linux-lts-headers` -
    - `linux-firmware` - Default set of Firmware files for Linux. (Meta-package containing many common hardware-specific firmware packages such as `linux-firmware-intel`)
    - `intel-ucode` - Microcode updates for Intel CPUs. Use `amd-ucode` if you have an AMD CPU.
    - `efibootmgr` -
    - `limine` - The bootloader
    - `networkmanager` - "Network connection manager and user applications"
    - `btrfs-progs` - User-space utilities for Btrfs filesystem
    - `zram-generator` - "Systemd unit generator for zram devices"
    - `cryptsetup` - "Userspace setup tool for transparent encryption of block devices using dm-crypt"
    - `snapper` - Tool to manage BTRFS and LVM snapshots
    - `sudo` - Allows running commands as root
    - `man` - Allows reading man pages
    - `vim` - The Arch Linux of text editors
    - `nano` - Fallback text editor for babies
- Generate Fstab: `genfstab -U /mnt >> /mnt/etc/fstab`
  - Check if fstab is fine: `cat /mnt/etc/fstab`
- Chroot into the Arch system: `arch-chroot /mnt`
- Set timezone (in this case Asia/Karachi): `ln -sf /usr/share/zoneinfo/Asia/Karachi /etc/localtime`
  - Find your timezone in `/usr/share/zoneinfo`
- Sync system time to hardware clock: `hwclock --systohc`
- Edit (using vim, or... nano) `/etc/locale.gen` and uncomment entries for your locales. In this case, only `en_US.UTF-8 UTF-8` will be uncommented.
- Generate the locales: `locale-gen`
- Create and edit `/etc/locale.conf` and set the `LANG` variable to the desired locale. In this case : `LANG=en_US.UTF-8`
- **KEYMAP SETTINGS NOT INCLUDED HERE. REFER TO ONLINE GUIDES. SET KEYMAP ONLY BEFORE THIS POINT OF THE GUIDE**.
- Create and edit `/etc/hostname` and write the desired name of your computer in the first line.
- Edit `/etc/hosts` and write the following lines in the file:
  - `127.0.0.1 localhost`
  - `::1 localhost`
  - `127.0.1.1 <your_hostname>`
- Set the root password: `passwd`
- Create your user: `useradd -mG wheel <your_username>`
  - `-G wheel` adds your user to the administrative group
- Set password for your user: `passwd <your_username>`
- Open the sudoers file with the editor of your choice: `EDITOR=vim visudo`
  - Uncomment the line which says something like "Uncomment to let members of group wheel execute any action" and uncomment the line exactly BELOW it, by removing the #. This will grant superuser priviledges to your user.
  - It is recommended to use `visudo` instead of `vim /etc/sudoers` because `visudo` locks the file from simultaneous edits and also runs syntax checks to avoid committing an unreadable file.
- Enable NetworkManager now: `systemctl enable --now NetworkManager`
- Create Swapfile for hibernation:
  - Disable Btrfs COW on the swap directory: `chattr +C /.swap`
  - `btrfs filesystem mkswapfile --size 17G /.swap/swapfile`
  - `chmod 600 /.swap/swapfile`
  - `mkswap /.swap/swapfile`
  - `swapon /.swap/swapfile`
- Determine resume offset for the swapfile (AI guide, not sure if it works):

```bash
filefrag -v /.swap/swapfile | sed -n '4p'
# extract the physical offset in 512-byte sectors:
filefrag -v /.swap/swapfile | awk 'NR==4 {print $4}'
# To extract only the first numeric start block:
filefrag -v /.swap/swapfile | awk 'NR==4 {print $4}' | sed -E 's/[^0-9].*//'
```

- That last numeric value is the starting extent in 512-byte sectors. Save it as `RESUME_OFFSET` for later.
- You will also need the UUID of the LUKS partition: `blkid /dev/nvme0n1p2`. Copy the `UUID=...` value
- Edit `/etc/mkinitcpio.conf` and set the HOOKS line to `HOOKS=(base systemd autodetect microcode modconf kms keyboard keymap sd-vconsole block sd-encrypt filesystems fsck)`
  - **NEEDS MORE EXPLANATION**
- Regenerate Initramfs: `mkinitcpio -P`
- Create EFI fallback: `mkdir -p /boot/EFI/BOOT` & `cp /usr/share/limine/BOOTX64.EFI /boot/EFI/BOOT/`
- Install Limine to the boot partition: `limine-install /dev/nvme0n1`
- Create and edit `/boot/limine.cfg`. Add the following:

```
timeout: 5

/Arch Linux
  protocol: linux
  path: boot():/vmlinuz-linux
  module_path: boot():/intel-ucode.img
  module_path: boot():/initramfs-linux.img
  cmdline: rd.luks.name={UUID}=cryptroot root=/dev/mapper/cryptroot rootflags=subvol=@ rw apparmor=1 security=apparmor resume=/dev/mapper/cryptroot resume_offset={RESUME_OFFSET} quiet
```

- Replace {UUID} with the UUID of the LUKS partition saved in above steps, and {RESUME_OFFSET} with the RESUME_OFFSET value saved in above steps.
- **ADD FALLBACK `linux-lts` KERNEL**
- Additional optional configuration for Limine:
  - To add `memtest`, install `memtest86+-efi` for UEFI, or `memtest86+` for BIOS, and add the following to `/boot/limine.cfg`:

```
# For UEFI
/Memtest86+
	protocol: efi
	path: boot():/memtest86+/memtest.efi

# Or for BIOS
/Memtest86+
    protocol: linux
    path: boot():/memtest86+/memtest.bin
```

- Setup pacman hook to deploy Limine whenever it is upgraded: Refer to this wiki: "https://wiki.archlinux.org/title/Limine#pacman_hook"
- Reboot:
  - Exit the chroot environment by typing `exit` or pressing `Ctrl+d`.
  - Unmount all partitions: `umount -R /mnt`
  - Restart the machine: `reboot`
  - Remove the installation medium

## After Installation

- Install yay AUR helper:
  - Install required tools: `sudo pacman -S base-devel git`
  - Clone yay repo: `git clone https://aur.archlinux.org/yay.git`
  - Navigate to the dir and build: `cd yay && makepkg -si`
  - Verify install: `yay --version`
- AppArmor Configuration
  - Install AppArmor: `sudo pacman -S apparmor`
  - Enable the AppArmor service (It is a system service): `sudo systemctl enable apparmor.service`
  - Add kernel parameters for AppArmor: Edit `/boot/limine.conf` and add `apparmor=1 security=apparmor` to the `cmdline` line (maybe after `rw`).
  - Reboot

---

## Limine Linux-LTS Setup

- Install `linux-lts` & `linux-lts-headers`
- Find the lts kernel EFI image: `ls /usr/lib/modules/*-lts/vmlinuz`
- Copy the vmlinuz file to `/boot`: `sudo cp /usr/lib/modules/*-lts/vmlinuz /boot/vmlinuz-linux-lts`
- Add the limine entry: Similar to the main entry but change the name to "Arch Linux (LTS)", change the boot path to `vmlinuz-linux-lts`, and change the initramfs path to `initramfs-linux-lts.img`
  - Limine entry will be auto-handled by `limine-mkinitcpio-hook` package if installed

## ZRAM Setup

- Install `zram-generator`
- Add zram kernel module: `echo zram | sudo tee /etc/modules-load.d/zram.conf` (Writes `zram` to `/etc/modules-load.d/zram.conf`)
- Configure zram-generator: copy configuration provided in this repo (`root/etc/systemd/zram-generator.conf`)
- Daemon-reload: `sudo systemctl daemon-reload`
- Enable zram: `sudo systemctl start systemd-zram-setup@zram0`

## Swap Setup (Btrfs)

- Create a swap file (4gb in this case): `btrfs filesystem mkswapfile --size 4g /.swap/swapfile`
  - **Already created during Arch Installation (see above)**
- Activate the swap file: `swapon /.swap/swapfile`
- Edit fstab to add an entry for swap: Write `/swap/swapfile none swap defaults,pri=0 0 0` to `/etc/fstab`
  - The priority can be changed by setting `pri=` to the desired value.
