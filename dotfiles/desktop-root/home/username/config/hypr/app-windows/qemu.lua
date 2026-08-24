hl.window_rule({
    name = "qemu-rules",
    match = {
        class = "qemu"
    },
    -- Dynamic effects
    opacity = "1.0 override 1.0 override",
})
