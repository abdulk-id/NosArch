import subprocess

from gi.repository import GObject, Nautilus


class TerminalMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def get_background_items(self, folder):
        item = Nautilus.MenuItem(
            name="Terminal::OpenHere",
            label="Open in Terminal",
            tip="Open Terminal in this directory",
        )
        item.connect("activate", self.activate, folder)
        return [item]

    def activate(self, menu, folder):
        path = folder.get_location().get_path()
        subprocess.Popen(["xdg-terminal-exec", f"--dir={path}"])
