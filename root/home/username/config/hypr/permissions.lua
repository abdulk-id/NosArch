-- === PERMISSIONS ===
-- See https://wiki.hypr.land/Configuring/Permissions/

-- Please note permission changes here require a Hyprland restart
-- and are not applied on-the-fly for security reasons

hl.config({
    ecosystem = {
        enforce_permissions = true
    }
})

-- hl.permission({ binary = "/usr/(bin|local/bin)/hyprpm", type = "plugin", mode = "allow" })
hl.permission({
    binary = "/usr/(lib|libexec|lib64)/xdg-desktop-portal-hyprland",
    type = "screencopy",
    mode = "allow",
})

hl.permission({ binary = "/usr/bin/grim", type = "screencopy", mode = "allow" })
hl.permission({ binary = "/usr/bin/hyprshot", type = "screencopy", mode = "allow" })
hl.permission({ binary = "/usr/bin/hyprpicker", type = "screencopy", mode = "allow" })

hl.permission({ binary = "/usr/bin/hyprlock", type = "screencopy", mode = "allow" })
