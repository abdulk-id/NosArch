Name = "share"
NamePretty = "share"
--Icon = "preferences-system-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "    Share Clipboard",
            Value = "nosarch-share clipboard"
        },
        {
            Text = "    Share Files",
            Value = "nosarch-share files"
        },
        {
            Text = "    Share Folder",
            Value = "nosarch-share folder"
        },
        {
            Text = "    Share Text",
            Value = "nosarch-share text"
        }
    }
end
