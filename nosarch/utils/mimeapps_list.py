from config import CONFIG

desktop_mimes: dict[str, str] = {
    "inode/directory": "org.gnome.Nautilus.desktop",
    # Browser
    "x-scheme-handler/http": "zen.desktop",
    "x-scheme-handler/https": "zen.desktop",
    "x-scheme-handler/chrome": "zen.desktop",
    # Images
    "image/png": "org.gnome.Loupe.desktop",
    "image/jpeg": "org.gnome.Loupe.desktop",
    "image/gif": "org.gnome.Loupe.desktop",
    "image/webp": "org.gnome.Loupe.desktop",
    "image/bmp": "org.gnome.Loupe.desktop",
    "image/tiff": "org.gnome.Loupe.desktop",
    "image/svg+xml": "org.gnome.Loupe.desktop",
    # PDF
    "application/pdf": "org.gnome.Papers.desktop",
    # Video
    "video/mp4": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-msvideo": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-matroska": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-flv": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-ms-wmv": "io.github.celluloid_player.Celluloid.desktop",
    "video/mpeg": "io.github.celluloid_player.Celluloid.desktop",
    "video/ogg": "io.github.celluloid_player.Celluloid.desktop",
    "video/webm": "io.github.celluloid_player.Celluloid.desktop",
    "video/quicktime": "io.github.celluloid_player.Celluloid.desktop",
    "video/3gpp": "io.github.celluloid_player.Celluloid.desktop",
    "video/3gpp2": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-ms-asf": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-ogm+ogg": "io.github.celluloid_player.Celluloid.desktop",
    "video/x-theora+ogg": "io.github.celluloid_player.Celluloid.desktop",
    "application/ogg": "io.github.celluloid_player.Celluloid.desktop",
    # Text
    "text/plain": "org.gnome.TextEditor.desktop",
    "text/english": "org.gnome.TextEditor.desktop",
}

dev_mimes: dict[str, str] = {
    # Code files
    "application/json": "dev.zed.Zed.desktop",
    "application/xml": "dev.zed.Zed.desktop",
    "application/x-desktop=dev": "zed.Zed.desktop;",
    "application/x-shellscript": "dev.zed.Zed.desktop",
    "text/css": "dev.zed.Zed.desktop",
    "text/x-makefile": "dev.zed.Zed.desktop",
    "text/x-c": "dev.zed.Zed.desktop",
    "text/x-c++": "dev.zed.Zed.desktop",
    "text/x-c++hdr": "dev.zed.Zed.desktop",
    "text/x-c++src": "dev.zed.Zed.desktop",
    "text/x-chdr": "dev.zed.Zed.desktop",
    "text/x-csrc": "dev.zed.Zed.desktop",
    "text/x-java": "dev.zed.Zed.desktop",
    "text/x-moc": "dev.zed.Zed.desktop",
    "text/x-pascal": "dev.zed.Zed.desktop",
    "text/x-tcl": "dev.zed.Zed.desktop",
    "text/x-tex": "dev.zed.Zed.desktop",
    "text/xml": "dev.zed.Zed.desktop",
    "text/x-shellscript": "dev.zed.Zed.desktop",
    # GitHub Handler
    "x-scheme-handler/github-app": "github-handler.desktop",
    "x-scheme-handler/ghapp": "github-handler.desktop",
    "x-scheme-handler/gh": "github-handler.desktop",
    # OpenCode Handler
    "x-scheme-handler/opencode": "opencode.desktop",
}


def get_mimeapps_content() -> str:
    lines: list[str] = ["[Default Applications]"]

    for mime, app in desktop_mimes.items():
        lines.append(f"{mime}={app}")

    if CONFIG["%DEV_PROFILE%"] == "true":
        lines.append("\t")
        for mime, app in dev_mimes.items():
            lines.append(f"{mime}={app}")

    return "\n".join(lines) + "\n"
