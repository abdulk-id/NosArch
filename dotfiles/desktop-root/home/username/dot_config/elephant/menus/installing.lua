-- Managed by NosArch

Name = "installing"
NamePretty = "Install package"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

-- Which packaging methods this machine can actually use right now. The CLI answers, so a
-- method whose module is disabled, or whose runtime was removed by hand, never shows up.
local function available_methods()
    local handle = io.popen("nosarch-package list-methods 2>/dev/null")

    if not handle then
        return {}
    end

    local methods = {}

    for raw in handle:lines() do
        local name = raw:match("^%s*(.-)%s*$")

        if #name > 0 then
            methods[#methods + 1] = name
        end
    end

    handle:close()

    return methods
end

-- Display order is fixed here rather than taken from the CLI, so the menu reads the same on
-- every machine and only the set of entries changes.
local METHODS = {
    { name = "arch", icon = "󰣇", label = "Arch repositories" },
    { name = "aur", icon = "󰣇", label = "AUR" },
    { name = "appimage", icon = "󰆧", label = "AppImage" },
    { name = "flatpak", icon = "󰏖", label = "Flatpak" },
    { name = "homebrew", icon = "󰂘", label = "Homebrew" },
    { name = "snap", icon = "󰋊", label = "Snap" },
}

function GetEntries()
    local available = available_methods()

    if #available == 0 then
        return {
            {
                Text = "󰋗    No packaging methods available",
                Value = "nosarch-launch-tui nosarch-package help",
            },
        }
    end

    local entries = {}

    for _, method in ipairs(METHODS) do
        for _, name in ipairs(available) do
            if name == method.name then
                -- An AppImage install opens a file dialog, which needs the graphical session
                -- to stay alive, so it is not run inside a terminal.
                local value = "nosarch-package install " .. method.name

                if method.name ~= "appimage" then
                    value = "nosarch-launch-tui " .. value
                end

                table.insert(entries, {
                    Text = method.icon .. "    " .. method.label,
                    Value = value,
                })
            end
        end
    end

    return entries
end
