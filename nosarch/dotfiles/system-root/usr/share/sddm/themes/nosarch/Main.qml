// Managed by NosArch
// Copied from Omarchy
// https://github.com/omacom/omarchy/blob/81fd2d23ca6e3462183a4dc8360de3113fa8d80c/default/sddm/omarchy/Main.qml

import QtQuick 2.0
import SddmComponents 2.0

Rectangle {
    id: root
    width: 640
    height: 480
    color: "#1a1b26"

    // lastUser is empty until someone has logged in once. A password-only theme then submits a blank name.
    property string currentUser: {
        var last = userModel.lastUser || "";
        if (last.length > 0)
            return last;
        if (userModel.rowCount() < 1)
            return "";
        // NameRole. SDDM's user model does not expose it by name; Qt.UserRole + 1 is 257.
        var name = userModel.data(userModel.index(0, 0), 257);
        return name ? name.toString() : "";
    }
    property bool loginFailed: false
    property int sessionIndex: {
        var rows = sessionModel.rowCount();
        var fallback = -1;
        for (var i = 0; i < rows; i++) {
            var name = (sessionModel.data(sessionModel.index(i, 0), Qt.DisplayRole) || "").toString().toLowerCase();
            if (name.indexOf("uwsm") !== -1)
                return i;
            if (fallback < 0 && name.indexOf("hyprland") !== -1)
                fallback = i;
        }
        if (fallback >= 0)
            return fallback;
        if (sessionModel.lastIndex >= 0)
            return sessionModel.lastIndex;
        return 0;
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.loginFailed = true;
            password.text = "";
            password.focus = true;
        }
        function onLoginSucceeded() {
            root.loginFailed = false;
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 40

        Image {
            id: logo
            source: "logo.png"
            width: Math.min(sourceSize.width, root.width * 0.8)
            height: sourceSize.width > 0 ? Math.round(width * sourceSize.height / sourceSize.width) : 0
            fillMode: Image.PreserveAspectFit
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 15

            Image {
                source: root.loginFailed ? "lock-failed.png" : "lock.png"
                width: 34
                height: 38
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter
            }

            Item {
                width: entry.width
                height: entry.height

                Image {
                    id: entry
                    source: root.loginFailed ? "entry-failed.png" : "entry.png"
                    anchors.centerIn: parent
                }

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5

                    Repeater {
                        model: Math.min(password.text.length, 21)

                        Image {
                            source: "bullet.png"
                            width: 7
                            height: 7
                        }
                    }
                }

                TextInput {
                    id: password
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    verticalAlignment: TextInput.AlignVCenter
                    echoMode: TextInput.Password
                    font.family: "JetBrainsMono Nerd Font"
                    font.pixelSize: 24
                    font.letterSpacing: 5
                    passwordCharacter: "\u2022"
                    color: "transparent"
                    selectionColor: "transparent"
                    selectedTextColor: "transparent"
                    cursorDelegate: Item {}
                    focus: true

                    onTextChanged: root.loginFailed = false

                    Keys.onPressed: {
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            sddm.login(root.currentUser, password.text, root.sessionIndex);
                            event.accepted = true;
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: password.forceActiveFocus()
}
