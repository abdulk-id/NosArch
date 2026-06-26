//@ pragma UseQApplication

import Quickshell

import "shell/topisland"
import "shell/osds"

ShellRoot {
    id: shell

    TopIsland {}

    ProgressOSDPanel {}
    MediaOsd {}
}
