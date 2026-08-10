Name = "packages"
NamePretty = "Packages"
--Icon = "system-software-install-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󰣇    Install Arch package",
            Value = "nosarch-launch-tui nosarch-package install arch"
        },
        {
            Text = "󰣇    Install AUR package",
            Value = "nosarch-launch-tui nosarch-package install aur"
        },
        {
            Text = "    Install Flatpak package",
            Value = "nosarch-launch-tui nosarch-package install flatpak"
        },
        {
            Text = "    Update packages",
            Value = "nosarch-launch-tui nosarch-package update"
        },
        {
            Text = "󰭌    Remove package",
            Value = "nosarch-launch-tui nosarch-package remove"
        },
        {
            Text = "    Clean system",
            Value = "nosarch-launch-tui nosarch-package remove-unused"
        }
    }
end
