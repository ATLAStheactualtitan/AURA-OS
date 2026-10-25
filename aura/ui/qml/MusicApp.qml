import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: app
    anchors.fill: parent
    property string pid: "all"
    property string sortKey: ""
    property var tracksModel: []
    property bool outputsOpen: false
    property string assignSlot: ""
    property var devices: []
    property var assigned: ({})
    property var plists: []

    function reload() {
        plists = aura.playlists()
        var t = aura.tracks(pid, search.text)
        if (sortKey) t.sort(function (a, b) { return a[sortKey] < b[sortKey] ? -1 : 1 })
        tracksModel = t
        devices = aura.audioDevices()
        assigned = aura.outputAssignments()
    }
    function plName() { for (var i = 0; i < plists.length; i++) if (plists[i].id === pid) return plists[i].name; return "Library" }
    function step(s) {
        var i = 0
        for (var k = 0; k < plists.length; k++) if (plists[k].id === pid) i = k
        pid = plists[(i + s + plists.length) % plists.length].id
        reload()
    }
    Component.onCompleted: reload()
    onPidChanged: reload()
    Connections {
        target: aura
        function onMusicChanged() { app.reload() }
        function onUiRequest(name, p) {
            if (name === "music_filter") { search.text = p.text; app.reload() }
            else if (name === "music_search") search.forceActiveFocus()
            else if (name === "music_refresh") app.reload()
            else if (name === "music_sort") { app.sortKey = p.key; app.reload() }
            else if (name === "music_playlist_step") app.step(p.step)
            else if (name === "show_outputs") { app.outputsOpen = true; app.devices = aura.audioDevices() }
            else if (name === "assign_output") { app.outputsOpen = true; app.assignSlot = p.slot; app.devices = aura.audioDevices() }
        }
    }
    Timer { interval: 700; running: app.visible; repeat: true
            onTriggered: { nowText.text = aura.nowPlaying(); playBtn.playing = aura.isPlaying() } }

    // Sidebar: playlist containers
    Rectangle {
        id: side; width: 180; height: parent.height; color: Qt.rgba(0, 0, 0, 0.18)
        Text { x: 16; y: 14; text: "PLAYLISTS"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.5; font.family: Theme.family }
        ListView {
            id: plView; anchors.fill: parent; anchors.topMargin: 36; model: app.plists; clip: true
            delegate: Rectangle {
                id: pld
                required property var modelData
                property string auraType: "playlist"
                property var auraData: ({ id: modelData.id, name: modelData.name })
                width: ListView.view.width - 12; x: 6; height: 36; radius: 9
                color: app.pid === modelData.id ? Qt.rgba(0.49, 0.61, 1, 0.22) : (pm.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent")
                Text { x: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; color: Theme.text; font.pixelSize: 13; font.family: Theme.family; elide: Text.ElideRight; width: parent.width - 24 }
                MouseArea { id: pm; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton; onClicked: app.pid = modelData.id }
            }
        }
    }

    // Main container: current playlist
    Item {
        id: main
        anchors { left: side.right; right: parent.right; top: parent.top; bottom: foot.top }
        property string auraType: "playlist"
        property var auraData: ({ id: app.pid, name: app.plName() })

        TextField {
            id: search; x: 16; y: 12; width: parent.width - 32; height: 36
            placeholderText: "Search " + app.plName() + " (FIND ↑)"
            color: Theme.text; font.family: Theme.family; placeholderTextColor: Theme.dim
            background: Rectangle { radius: 18; color: Qt.rgba(1, 1, 1, 0.06); border.color: search.activeFocus ? Theme.accent : Theme.border }
            onTextChanged: app.reload()
        }
        ListView {
            id: tv; anchors { fill: parent; topMargin: 58; leftMargin: 10; rightMargin: 10 } clip: true
            model: app.tracksModel; spacing: 2
            Text { visible: tv.count === 0; anchors.centerIn: parent; text: "No tracks here"; color: Theme.dim; font.family: Theme.family }
            delegate: Rectangle {
                id: row
                objectName: "song-" + index
                required property var modelData
                required property int index
                property string auraType: "song"
                property var auraData: ({ path: modelData.path, title: modelData.title, artist: modelData.artist })
                width: ListView.view.width; height: 46; radius: 10
                color: sel.containsMouse ? Qt.rgba(1, 1, 1, 0.07) : (index % 2 ? "transparent" : Qt.rgba(1, 1, 1, 0.02))
                Text { x: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.fav ? "★" : "♪"; color: modelData.fav ? Theme.warn : Theme.accent; font.pixelSize: 15 }
                Column {
                    x: 44; anchors.verticalCenter: parent.verticalCenter
                    Text { text: modelData.title; color: Theme.text; font.pixelSize: 14; font.family: Theme.family; font.weight: Font.Medium }
                    Text { text: modelData.artist + " · " + modelData.album; color: Theme.dim; font.pixelSize: 11; font.family: Theme.family }
                }
                MouseArea { id: sel; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton
                            onDoubleClicked: aura.playPlain(modelData.path) }
            }
        }
    }

    // Output panel
    Rectangle {
        id: outs
        visible: app.outputsOpen
        anchors { right: parent.right; top: parent.top; bottom: foot.top; margins: 10 }
        width: 330; radius: 14; color: Theme.glassLight; border.color: Theme.border
        Text { x: 16; y: 14; text: "Audio outputs"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.family }
        Text { anchors.right: parent.right; anchors.rightMargin: 14; y: 12; text: "✕"; color: Theme.dim; font.pixelSize: 16
               MouseArea { anchors.fill: parent; onClicked: app.outputsOpen = false } }
        Text { x: 16; y: 40; width: parent.width - 32; wrapMode: Text.Wrap; color: Theme.dim; font.pixelSize: 11; font.family: Theme.family
               text: app.assignSlot ? "Choose a device for slot " + app.assignSlot + "."
                                    : "Song → ACT ← → output ↓ → slot. Assign a device to LEFT / UP / RIGHT; the mapping never changes unless you change it." }
        ListView {
            anchors { fill: parent; topMargin: 92; margins: 10 } clip: true; model: app.devices; spacing: 6
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 74; radius: 10; color: Qt.rgba(1, 1, 1, 0.05)
                Text { x: 12; y: 8; text: modelData.name + (modelData.default ? "  (default)" : ""); color: Theme.text; font.pixelSize: 13; font.family: Theme.family
                       width: parent.width - 24; elide: Text.ElideRight }
                Row {
                    x: 10; y: 36; spacing: 6
                    Repeater {
                        model: ["LEFT", "UP", "RIGHT"]
                        delegate: Button {
                            required property string modelData
                            property var devd: parent.parent.modelData
                            property bool on: !!(app.assigned[modelData] && app.assigned[modelData].target === devd.id)
                            text: (on ? "✓ " : "") + modelData
                            height: 28
                            background: Rectangle { radius: 8; color: on ? Qt.rgba(0.29, 0.84, 0.76, 0.3) : Qt.rgba(1, 1, 1, 0.08)
                                                    border.width: app.assignSlot === modelData ? 2 : 0; border.color: Theme.accent }
                            contentItem: Text { text: parent.text; color: Theme.text; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: { aura.assignOutput(modelData, devd.id, devd.name); app.assignSlot = "" }
                        }
                    }
                }
            }
            Text { visible: app.devices.length === 0; anchors.centerIn: parent; color: Theme.warn; text: "No output devices reported"; font.family: Theme.family }
        }
        Column {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 12 } spacing: 3
            Repeater {
                model: ["LEFT", "UP", "RIGHT"]
                delegate: Text {
                    required property string modelData
                    property var a: app.assigned[modelData]
                    property bool present: a ? app.devices.some(function (d) { return d.id === a.target }) : false
                    font.family: Theme.family; font.pixelSize: 11; color: !a ? Theme.dim : (present ? Theme.accent2 : Theme.warn)
                    text: modelData + " → " + (a ? a.label + (present ? "  ✓ connected" : "  ⊘ unavailable") : "unassigned")
                }
            }
        }
    }

    // Footer: transport
    Rectangle {
        id: foot; anchors { left: side.right; right: parent.right; bottom: parent.bottom } height: 56; color: Qt.rgba(0, 0, 0, 0.22)
        Rectangle {
            id: playBtn; property bool playing: false
            x: 16; anchors.verticalCenter: parent.verticalCenter; width: 36; height: 36; radius: 18; color: Theme.accent
            Text { anchors.centerIn: parent; text: playBtn.playing ? "❚❚" : "▶"; color: "#0b0e14"; font.pixelSize: 13 }
            MouseArea { anchors.fill: parent; onClicked: { aura.invoke("music.toggle", "app:music", {}) } }
        }
        Text { id: nowText; x: 64; anchors.verticalCenter: parent.verticalCenter; color: Theme.text; font.family: Theme.family; font.pixelSize: 13
               width: parent.width - 220; elide: Text.ElideRight; text: "" }
        Button {
            anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: "Outputs"
            onClicked: { app.outputsOpen = !app.outputsOpen; app.devices = aura.audioDevices() }
        }
    }
}
