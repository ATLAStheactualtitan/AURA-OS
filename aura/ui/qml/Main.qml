import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    visible: true
    width: 1440; height: 900
    visibility: fullscreenMode ? Window.FullScreen : Window.Windowed
    title: "AURA"
    color: Theme.bg
    palette.button: "#3a3a3c"
    palette.buttonText: Theme.text
    palette.window: "#1c1c1e"
    palette.windowText: Theme.text
    palette.base: "#2c2c2e"
    palette.text: Theme.text
    palette.highlight: Theme.accent
    palette.highlightedText: "#0b0e14"
    palette.placeholderText: Theme.dim

    property int zTop: 10
    property bool launcherOpen: false
    readonly property var appDefs: [
        { id: "music", title: "Music", glyph: "♪", tint: "#ff375f" },
        { id: "files", title: "Files", glyph: "▣", tint: "#0a84ff" },
        { id: "editor", title: "Editor", glyph: "✎", tint: "#ff9f0a" },
        { id: "lab", title: "Gesture Lab", glyph: "◎", tint: "#bf5af2" },
        { id: "settings", title: "Settings", glyph: "⚙", tint: "#98989d" }
    ]
    function win(id) { return ({ music: musicWin, files: filesWin, editor: editorWin, lab: labWin, settings: settingsWin })[id] }
    function openApp(id) {
        var w = win(id); if (!w) return
        w.open(); raise(w); launcherOpen = false
    }
    function raise(w) { zTop += 1; w.z = zTop }

    // Resolve the gesture context from whatever item is under the pointer (deepest item that declares one).
    function contextAt(x, y) {
        var item = shell, px = x, py = y, found = { type: "desktop", data: {} }
        for (var guard = 0; guard < 64; guard++) {
            // Flickable.children are the contentItem's children, so offset by the content position.
            var lx = px, ly = py
            if (item.flickableDirection !== undefined && item.contentItem) { lx -= item.contentItem.x; ly -= item.contentItem.y }
            var ch = item.children, best = null, bz = -1e9
            for (var i = 0; i < ch.length; i++) {
                var c = ch[i]
                if (!c.visible || c.width === undefined) continue
                if (lx >= c.x && ly >= c.y && lx < c.x + c.width && ly < c.y + c.height && c.z >= bz) { best = c; bz = c.z }
            }
            if (!best) break
            px = lx - best.x; py = ly - best.y; item = best
            if (item.auraType !== undefined && item.auraType !== "") found = { type: item.auraType, data: item.auraData || {} }
        }
        return found
    }

    Connections {
        target: aura
        function onUiRequest(name, p) {
            if (name === "open_app") root.openApp(p.app)
            else if (name === "open_launcher") { root.launcherOpen = true; launchSearch.forceActiveFocus() }
            else if (name === "show_desktop") { for (var i = 0; i < appDefs.length; i++) win(appDefs[i].id).visible = false }
            else if (name === "editor_open") root.openApp("editor")
            else if (name === "editor_new") root.openApp("editor")
            else if (name === "files_open" || name === "files_search" || name === "files_transfer") root.openApp("files")
            else if (name === "show_outputs" || name === "assign_output" || name === "music_filter" || name === "music_search") root.openApp("music")
        }
        function onToast(text, ok, kind) { toasts.append({ text: text, kind: kind, ok: ok }) }
        function onPromptRequested(title, value, token) { prompt.start(title, value, token) }
        function onConfirmRequested(text, token) { confirm.start(text, token) }
    }

    // ------------------------------------------------------------------ desktop shell
    Item {
        id: shell
        anchors.fill: parent
        property string auraType: "desktop"
        property var auraData: ({})

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0; color: "#1b1446" }
                GradientStop { position: 0.5; color: "#3b1d6e" }
                GradientStop { position: 1; color: "#0f2a5c" }
            }
            Rectangle { x: parent.width * 0.55; y: -parent.height * 0.2; width: parent.height * 1.1; height: width; radius: width / 2; color: "#ff6ac1"; opacity: 0.12 }
            Rectangle { x: -parent.width * 0.1; y: parent.height * 0.45; width: parent.height * 0.9; height: width; radius: width / 2; color: "#64d2ff"; opacity: 0.1 }
        }
        Text { anchors.centerIn: parent; text: "AURA"; font.pixelSize: 120; font.weight: Font.Thin; font.letterSpacing: 24; color: "#ffffff"; opacity: 0.04; font.family: Theme.family }
        Text { anchors.horizontalCenter: parent.horizontalCenter; y: parent.height / 2 + 70; color: Theme.dim; opacity: 0.5; font.pixelSize: 12; font.family: Theme.family
               text: "Right-click the desktop, hold, and drag.  ←  ↑  →  ↓" }

        // Desktop icons
        Column {
            x: 28; y: 28; spacing: 14
            Repeater {
                model: root.appDefs
                delegate: Item {
                    id: ic
                    required property var modelData
                    property string auraType: "app_icon"
                    property var auraData: ({ app: modelData.id, title: modelData.title })
                    width: 84; height: 88
                    Rectangle { id: tile; width: 58; height: 58; radius: 13; anchors.horizontalCenter: parent.horizontalCenter
                        color: modelData.tint; opacity: im.containsMouse ? 1 : 0.92; border.width: 0
                        Text { anchors.centerIn: parent; text: modelData.glyph; color: "#ffffff"; font.pixelSize: 28 } }
                    Text { anchors.top: tile.bottom; anchors.topMargin: 6; anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title; color: Theme.text; font.pixelSize: 12; font.family: Theme.family }
                    MouseArea { id: im; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton; onDoubleClicked: root.openApp(modelData.id) }
                }
            }
        }

        // Windows
        AppWindow { id: musicWin; appId: "music"; title: "Music"; tint: "#7c9cff"; x: 170; y: 60; width: 860; height: 540
            onRaised: root.raise(musicWin); MusicApp {} }
        AppWindow { id: filesWin; appId: "files"; title: "Files"; tint: "#ffb454"; x: 260; y: 110; width: 760; height: 500
            onRaised: root.raise(filesWin); FilesApp {} }
        AppWindow { id: editorWin; appId: "editor"; title: "Editor"; tint: "#4ad7c1"; x: 330; y: 90; width: 700; height: 520
            onRaised: root.raise(editorWin); EditorApp {} }
        AppWindow { id: labWin; appId: "lab"; title: "Gesture Lab"; tint: "#c792ea"; x: 200; y: 70; width: 960; height: 600
            onRaised: root.raise(labWin); LabApp {} }
        AppWindow { id: settingsWin; appId: "settings"; title: "Settings"; tint: "#8e98b0"; x: 360; y: 100; width: 620; height: 620
            onRaised: root.raise(settingsWin); SettingsApp {} }

        // Panel
        Rectangle {
            id: panel
            anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 14
            z: 100000
            width: panelRow.implicitWidth + 28; height: 64; radius: 22; color: Theme.glass; border.color: Qt.rgba(1, 1, 1, 0.18)
            property string auraType: "desktop"
            Row {
                id: panelRow; anchors.centerIn: parent; spacing: 10
                Rectangle { width: 44; height: 44; radius: 11; color: root.launcherOpen ? Theme.accent : Qt.rgba(1, 1, 1, 0.14)
                    Text { anchors.centerIn: parent; text: "◈"; color: root.launcherOpen ? "#0b0e14" : Theme.text; font.pixelSize: 20 }
                    MouseArea { anchors.fill: parent; acceptedButtons: Qt.LeftButton; onClicked: { root.launcherOpen = !root.launcherOpen; if (root.launcherOpen) launchSearch.forceActiveFocus() } } }
                Repeater { model: root.appDefs
                    delegate: Rectangle { required property var modelData
                        property var w: root.win(modelData.id)
                        width: 44; height: 44; radius: 11; color: modelData.tint; opacity: pa.containsMouse ? 1 : 0.92
                        scale: pa.containsMouse ? 1.12 : 1
                        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
                        Text { anchors.centerIn: parent; text: modelData.glyph; color: "#ffffff"; font.pixelSize: 20 }
                        Rectangle { visible: w.visible; width: 4; height: 4; radius: 2; color: Theme.text; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.bottom; anchors.topMargin: 3 }
                        MouseArea { id: pa; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton; onClicked: root.openApp(modelData.id) } } }
                Rectangle { width: 1; height: 28; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
                Text { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 11; font.family: Theme.family; color: Theme.dim
                       text: "Guidance L" + aura.guidanceInfo.level + " · " + aura.guidanceInfo.name }
                Text { id: clock; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13; color: Theme.text; font.family: Theme.family
                       text: Qt.formatTime(new Date(), "hh:mm")
                       Timer { interval: 15000; running: true; repeat: true; onTriggered: clock.text = Qt.formatTime(new Date(), "hh:mm") } }
            }
        }

        // Launcher
        Rectangle {
            id: launcher
            visible: root.launcherOpen; z: 99999
            anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: panel.top; anchors.bottomMargin: 12
            width: 520; height: 300; radius: 20; color: Theme.glassLight; border.color: Theme.border
            property string auraType: "desktop"
            TextField { id: launchSearch; x: 18; y: 18; width: parent.width - 36; height: 38; placeholderText: "Search applications…"; color: Theme.text; placeholderTextColor: Theme.dim
                background: Rectangle { radius: 19; color: Qt.rgba(1, 1, 1, 0.07); border.color: launchSearch.activeFocus ? Theme.accent : Theme.border }
                onAccepted: { for (var i = 0; i < root.appDefs.length; i++) if (root.appDefs[i].title.toLowerCase().indexOf(text.toLowerCase()) >= 0) { root.openApp(root.appDefs[i].id); text = ""; return } } }
            GridLayout {
                x: 18; y: 74; width: parent.width - 36; columns: 4; rowSpacing: 12; columnSpacing: 12
                Repeater {
                    model: root.appDefs.filter(function (a) { return a.title.toLowerCase().indexOf(launchSearch.text.toLowerCase()) >= 0 })
                    delegate: Item { required property var modelData; Layout.preferredWidth: 110; Layout.preferredHeight: 100
                        property string auraType: "app_icon"; property var auraData: ({ app: modelData.id, title: modelData.title })
                        Rectangle { anchors.fill: parent; radius: 16; color: Qt.rgba(1, 1, 1, lm.containsMouse ? 0.12 : 0.05)
                            Text { anchors.horizontalCenter: parent.horizontalCenter; y: 16; text: modelData.glyph; color: modelData.tint; font.pixelSize: 34 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; y: 66; text: modelData.title; color: Theme.text; font.pixelSize: 12; font.family: Theme.family } }
                        MouseArea { id: lm; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton; onClicked: root.openApp(modelData.id) } }
                }
            }
        }
    }

    // ------------------------------------------------------------------ gesture input (right button only)
    MouseArea {
        id: gestureInput
        anchors.fill: parent
        z: 200000
        acceptedButtons: aura.gesture.active && aura.gesture.mode === "menu" ? Qt.AllButtons : Qt.RightButton
        onPressed: (m) => {
            if (aura.gesture.active && aura.gesture.mode === "menu") aura.closeMenu()
            if (m.button !== Qt.RightButton) return
            var c = root.contextAt(m.x, m.y)
            aura.beginGesture(c.type, c.data, m.x, m.y)
        }
        onPositionChanged: (m) => { if (pressed) aura.moveGesture(m.x, m.y) }
        onReleased: (m) => { if (m.button === Qt.RightButton) aura.endGesture(m.x, m.y) }
        onCanceled: aura.cancelGesture()
    }
    GestureOverlay { id: gestureOverlay; z: 200001 }
    Shortcut { sequence: "Escape"; enabled: aura.gesture.active; onActivated: aura.cancelGesture() }
    Shortcut { sequence: "Escape"; enabled: !aura.gesture.active && root.launcherOpen; onActivated: root.launcherOpen = false }
    Shortcut { sequence: "Ctrl+Q"; onActivated: Qt.quit() }

    // ------------------------------------------------------------------ toasts, prompt, confirm
    ListModel { id: toasts }
    Column {
        z: 300000; anchors.right: parent.right; anchors.rightMargin: 18; anchors.top: parent.top; anchors.topMargin: 18; spacing: 8
        Repeater {
            model: toasts
            delegate: Rectangle {
                id: t
                required property int index
                required property string text
                required property string kind
                width: Math.min(420, tt.implicitWidth + 56); height: tt.implicitHeight + 24; radius: 14
                color: Theme.glassLight; border.width: 1.5
                border.color: kind === "ok" ? Theme.accent2 : kind === "tip" ? Theme.accent : kind === "warn" ? Theme.warn : Theme.danger
                opacity: 0
                Component.onCompleted: { opacity = 1; life.start() }
                Behavior on opacity { NumberAnimation { duration: 200 } }
                Text { x: 14; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 14; color: t.border.color
                       text: t.kind === "ok" ? "✓" : t.kind === "tip" ? "💡" : t.kind === "warn" ? "⚠" : "✕" }
                Text { id: tt; x: 40; width: Math.min(360, implicitWidth); anchors.verticalCenter: parent.verticalCenter; text: t.text; wrapMode: Text.Wrap
                       color: Theme.text; font.pixelSize: 13; font.family: Theme.family }
                Timer { id: life; interval: t.kind === "tip" ? 7000 : 4200; onTriggered: { t.opacity = 0; rm.start() } }
                Timer { id: rm; interval: 220; onTriggered: if (t.index < toasts.count) toasts.remove(t.index) }
            }
        }
    }

    component Modal: Rectangle {
        id: m
        property int token: -1
        visible: false; z: 400000; anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.45)
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
    }
    Modal {
        id: prompt
        function start(title, value, tk) { token = tk; ptitle.text = title; pfield.text = value; visible = true; pfield.forceActiveFocus(); pfield.selectAll() }
        Rectangle { anchors.centerIn: parent; width: 420; height: 160; radius: 18; color: Theme.glassLight; border.color: Theme.border
            Text { id: ptitle; x: 22; y: 18; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: Theme.family }
            TextField { id: pfield; x: 22; y: 54; width: parent.width - 44; color: Theme.text; onAccepted: okb.clicked()
                background: Rectangle { radius: 10; color: Qt.rgba(1, 1, 1, 0.07); border.color: Theme.accent } }
            Row { anchors.right: parent.right; anchors.rightMargin: 22; y: 108; spacing: 8
                Button { text: "Cancel"; onClicked: prompt.visible = false }
                Button { id: okb; text: "OK"; onClicked: { prompt.visible = false; aura.promptDone(prompt.token, pfield.text) } } } }
    }
    Modal {
        id: confirm
        function start(text, tk) { token = tk; ctext.text = text; visible = true; cancelb.forceActiveFocus() }
        Rectangle { anchors.centerIn: parent; width: 440; height: 170; radius: 18; color: Theme.glassLight; border.color: Theme.warn
            Text { x: 22; y: 20; text: "⚠  Confirm destructive action"; color: Theme.warn; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: Theme.family }
            Text { id: ctext; x: 22; y: 58; width: parent.width - 44; wrapMode: Text.Wrap; color: Theme.text; font.pixelSize: 14; font.family: Theme.family }
            Row { anchors.right: parent.right; anchors.rightMargin: 22; y: 118; spacing: 8
                Button { id: cancelb; text: "Cancel"; onClicked: { confirm.visible = false; aura.confirmDone(confirm.token, false) } }
                Button { text: "Delete"; onClicked: { confirm.visible = false; aura.confirmDone(confirm.token, true) } } } }
    }
}
