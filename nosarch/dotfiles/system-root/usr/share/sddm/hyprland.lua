-- Managed by NosArch
-- Copied from Omarchy
-- https://github.com/omacom/omarchy/blob/81fd2d23ca6e3462183a4dc8360de3113fa8d80c/default/sddm/hyprland.lua

-- Minimal Hyprland config for the SDDM Wayland greeter.
-- SDDM starts the greeter itself after the compositor is ready.
-- The greeter runs as the sddm user, so it cannot load the user's Hyprland config.

local function read_vconsole()
    local values = {}
    local file = io.open("/etc/vconsole.conf", "r")
    if not file then
        return values
    end
    for line in file:lines() do
        local key, value = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if key and value then
            value = value:gsub("%s+#.*$", "")
            value = value:gsub('^"(.*)"$', "%1")
            value = value:gsub("^'(.*)'$", "%1")
            values[key] = value
        end
    end
    file:close()
    return values
end

-- Layouts that can't type Latin letters. A greeter that can't type Latin letters can't take a password.
local non_latin_layouts =
" af am ara bd bg by et ge gr il in iq ir kg kh kz la lk mk mm mn mv np rs ru sy th tj ua "

-- archinstall writes KEYMAP, not XKBLAYOUT. A keymap that is not an xkb layout name
-- leaves the greeter on us, so the password typed here is not the one the TTY accepts.
local keymap_layouts = {
    uk = "gb",
    sv = "se",
    ["br-abnt2"] = "br",
    ["de-latin1"] = "de",
    ["de-latin1-nodeadkeys"] = "de",
    ["fr-latin1"] = "fr",
    ["fr-latin9"] = "fr",
    ["pt-latin1"] = "pt",
    ["pt-latin9"] = "pt",
    dvorak = "us",
    colemak = "us",
}

local function layout_from_keymap(keymap)
    if keymap_layouts[keymap] then
        return keymap_layouts[keymap]
    end
    local base = keymap:match("^([%a]+)")
    return keymap_layouts[base] or base or "us"
end

local vconsole = read_vconsole()
local kb_layout = vconsole.XKBLAYOUT
local kb_variant = vconsole.XKBVARIANT or ""
local kb_options = ""

if not kb_layout or kb_layout == "" then
    local keymap = vconsole.KEYMAP or "us"
    kb_layout = layout_from_keymap(keymap)
    if kb_variant == "" then
        if keymap == "dvorak" or keymap == "colemak" then
            kb_variant = keymap
        elseif keymap:find("nodeadkeys", 1, true) then
            kb_variant = "nodeadkeys"
        end
    end
end

-- A non-Latin layout gets us in front, reachable back with Left Alt + Right Alt.
if non_latin_layouts:find(" " .. kb_layout:match("^[^,]*") .. " ", 1, true) then
    kb_layout = "us," .. kb_layout
    kb_variant = "," .. kb_variant
    kb_options = "grp:alts_toggle"
end

hl.config({
    input = {
        kb_layout = kb_layout,
        kb_variant = kb_variant,
        kb_options = kb_options,
    },

    misc = {
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        background_color = "rgb(000000)",
        force_default_wallpaper = 0,
    },

    animations = {
        enabled = false,
    },
})
