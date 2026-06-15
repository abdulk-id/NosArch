Name = "software"
NamePretty = "Software"
Icon = "system-software-install-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "Install package",
            Value = "nosarch-pkg-install",
            Icon = "system-software-install-symbolic",
            Weight = 10
        },
        {
            Text = "Install AUR package",
            Value = "nosarch-aur-install",
            Icon = "system-software-install-symbolic",
            Weight = 9
        },
        {
            Text = "Update",
            Value = "nosarch-update",
            Icon = "software-update-available-symbolic",
            Weight = 8
        },
        {
            Text = "Remove package",
            Value = "nosarch-pkg-remove",
            Icon = "edit-delete-symbolic",
            Weight = 7
        }
    }
end
