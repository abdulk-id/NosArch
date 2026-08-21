require("looknfeel")
require("autostart")
require("input")
require("binds.hyprbinds")
require("binds.mediabinds")
require("binds.userbinds")
require("permissions")
require("windows")

hl.config({
    ecosystem = {
        no_update_news = false,
        no_donation_nag = false,
    },

    xwayland = {
        force_zero_scaling = true,
    },
})

-- Added by hyprmoncfg: its generated monitor rules load last, so nothing before this can override the applied layout.
dofile(os.getenv("HOME") .. "/.config/hypr/hyprmoncfg-monitors.lua")
