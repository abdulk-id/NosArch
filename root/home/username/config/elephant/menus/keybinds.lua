Name = "keybinds"
NamePretty = "Hyprland Keybinds"
Cache = true
HideFromProviderlist = true

local function sh(cmd)
    local p = io.popen(cmd .. " 2>/dev/null")
    if not p then return nil end
    local out = p:read("*a")
    p:close()
    return out
end

local function trim(s)
    s = tostring(s or "")
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- Convert modmask to readable modifiers
local function modmask_to_mods(mask)
    mask = tonumber(mask) or 0

    local map = {
        [1] = "SHIFT",
        [4] = "CTRL",
        [8] = "ALT",
        [64] = "SUPER",
    }

    local mods = {}

    -- handle combinations explicitly
    local combos = {
        [0] = "",
        [1] = "SHIFT",
        [4] = "CTRL",
        [5] = "SHIFT CTRL",
        [8] = "ALT",
        [9] = "SHIFT ALT",
        [12] = "CTRL ALT",
        [13] = "SHIFT CTRL ALT",
        [64] = "SUPER",
        [65] = "SUPER SHIFT",
        [68] = "SUPER CTRL",
        [69] = "SUPER SHIFT CTRL",
        [72] = "SUPER ALT",
        [73] = "SUPER SHIFT ALT",
        [76] = "SUPER CTRL ALT",
        [77] = "SUPER SHIFT CTRL ALT",
    }

    return combos[mask] or ""
end

function GetEntries()
    local cmd = [[hyprctl -j binds | jq -r '
        .[] | "\(.modmask),\(.key),\(.description),\(.dispatcher),\(.arg)"
    ']]

    local raw = sh(cmd)
    if not raw or raw == "" then
        return {
            {
                Text = "Failed to load keybinds",
                Actions = { default = "lua:Noop" },
            },
        }
    end

    local rows = {}
    local max_len = 0

    for line in raw:gmatch("[^\r\n]+") do
        local modmask, key, desc = line:match("^(.-),(.-),(.-),(.-),(.*)$")
        if modmask then
            key = trim(key)
            desc = trim(desc)

            local mods = modmask_to_mods(modmask)

            local combo
            if mods ~= "" and key ~= "" then
                combo = mods .. " + " .. key
            elseif key ~= "" then
                combo = key
            else
                combo = "(unknown bind)"
            end

            local label = desc ~= "" and desc or combo

            if #label > max_len then
                max_len = #label
            end

            table.insert(rows, {
                label = label,
                combo = combo,
                has_desc = desc ~= ""
            })
        end
    end

    local entries = {}

    for _, row in ipairs(rows) do
        local text

        if row.has_desc then
            -- Fixed-width alignment like awk %-35s → %s
            text = string.format("%-35s -> %s", row.label, row.combo)
        else
            text = row.combo
        end

        table.insert(entries, {
            Text = text,
            Actions = { default = "lua:Noop" },
        })
    end

    return entries
end

function Noop()
end
