import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

Item {
    id: app
    anchors.fill: parent
    property string dir: ""
    property var entries: []
    property var roots: []
    property var marks: []
    property string selected: ""
    property var transfer: null
    property string query: ""

    function refresh() {
        roots = aura.roots(); marks = aura.bookmarks()
        if (!dir && roots.length) dir = roots[0]
        entries = dir ? aura.searchFiles(dir, query) : []
    }
    function open(p) { dir = p; query = ""; search.text = ""; selected = ""; refresh() }
    function parentOf(p) { var i = p.lastIndexOf("/"); return i > 0 ? p.substring(0, i) : "/" }
    Component.onCompleted: refresh()
    Connections {
        target: aura
        function onUiRequest(name, p) {
            if (name === "files_open") app.open(p.path)
            else if (name === "files_refresh") app.refresh()
            else if (name === "files_search") { app.dir = p.path; search.forceActiveFocus(); app.refresh() }
            else if (name === "files_transfer") app.transfer = { mode: p.mode, path: p.path }
        }
    }
    FolderDialog { id: fd; onAccepted: { aura.addRoot(selectedFolder.toString()); app.refresh() } }

    Rectangle {
        id: side; width: 190; height: parent.height; color: Qt.rgba(0, 0, 0, 0.18)
        property string auraType: "app:files"
        Column {
            x: 10; y: 12; width: parent.width - 20; spacing: 4
            Text { text: "AUTHORIZED FOLDERS"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4; font.family: Theme.family }
            Repeater { model: app.roots
                delegate: Rectangle { required property string modelData; width: parent.width; height: 30; radius: 8
                    color: sm.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                    Text { x: 8; anchors.verticalCenter: parent.verticalCenter; text: "▣ " + modelData.split("/").pop(); color: Theme.text; font.pixelSize: 12; width: parent.width - 12; elide: Text.ElideRight }
                    MouseArea { id: sm; anchors.fill: parent; hoverEnabled: true; onClicked: app.open(modelData) } } }
            Text { visible: app.marks.length > 0; text: "BOOKMARKS"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4; topPadding: 10; font.family: Theme.family }
            Repeater { model: app.marks
                delegate: Rectangle { required property string modelData; width: parent.width; height: 28; radius: 8
                    color: bm.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                    Text { x: 8; anchors.verticalCenter: parent.verticalCenter; text: "★ " + modelData.split("/").pop(); color: Theme.text; font.pixelSize: 12; width: parent.width - 12; elide: Text.ElideRight }
                    MouseArea { id: bm; anchors.fill: parent; hoverEnabled: true; onClicked: app.open(modelData) } } }
            Button { text: "Authorize folder…"; onClicked: fd.open() }
        }
    }

    Item {
        anchors { left: side.right; right: parent.right; top: parent.top; bottom: parent.bottom }
        Rectangle {
            id: top; width: parent.width; height: 48; color: "transparent"
            Row { x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                Button { text: "↑"; width: 34; onClicked: app.open(app.parentOf(app.dir)) }
                Text { anchors.verticalCenter: parent.verticalCenter; text: app.dir; color: Theme.dim; font.pixelSize: 12; font.family: Theme.family; width: 260; elide: Text.ElideMiddle }
            }
            TextField { id: search; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; width: 200; height: 32
                placeholderText: "Search folder (FIND ↑)"; color: Theme.text; placeholderTextColor: Theme.dim
                background: Rectangle { radius: 16; color: Qt.rgba(1, 1, 1, 0.06); border.color: search.activeFocus ? Theme.accent : Theme.border }
                onTextChanged: { app.query = text; app.refresh() } }
        }
        Rectangle {
            id: banner; visible: app.transfer !== null; y: top.height; width: parent.width; height: visible ? 40 : 0; color: Qt.rgba(0.77, 0.57, 0.92, 0.18)
            Text { x: 14; anchors.verticalCenter: parent.verticalCenter; color: Theme.text; font.family: Theme.family; font.pixelSize: 12
                   text: app.transfer ? app.transfer.mode.toUpperCase() + " “" + app.transfer.path.split("/").pop() + "” → open the destination folder, then press the button" : "" }
            Row { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                Button { text: app.transfer ? (app.transfer.mode === "move" ? "Move here" : "Copy here") : ""; onClicked: { aura.completeTransfer(app.transfer.mode, app.dir); app.transfer = null; app.refresh() } }
                Button { text: "Cancel"; onClicked: app.transfer = null }
            }
        }
        Item {
            id: pane
            property string auraType: "files_pane"
            property var auraData: ({ path: app.dir, name: app.dir.split("/").pop() })
            anchors { left: parent.left; right: parent.right; top: banner.bottom; bottom: parent.bottom }
            ListView {
                id: lv; anchors.fill: parent; anchors.margins: 8; clip: true; spacing: 1; model: app.entries
                Text { visible: lv.count === 0; anchors.centerIn: parent; text: "Empty"; color: Theme.dim }
                delegate: Rectangle {
                    id: fr
                    required property var modelData
                    property string auraType: modelData.isDir ? "folder_item" : "file_item"
                    property var auraData: ({ path: modelData.path, name: modelData.name, dir: app.dir })
                    width: ListView.view.width; height: 36; radius: 8
                    color: app.selected === modelData.path ? Qt.rgba(0.49, 0.61, 1, 0.25) : (fm.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent")
                    Text { x: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData.isDir ? "▸" : "·"; color: modelData.isDir ? Theme.warn : Theme.dim; font.pixelSize: 14 }
                    Text { x: 34; anchors.verticalCenter: parent.verticalCenter; text: modelData.name + (modelData.isDir ? "/" : ""); color: Theme.text; font.pixelSize: 13; font.family: Theme.family }
                    Text { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                           text: modelData.isDir ? "" : (modelData.size > 1024 ? Math.round(modelData.size / 1024) + " KB" : modelData.size + " B"); color: Theme.dim; font.pixelSize: 11 }
                    MouseArea { id: fm; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton
                        onClicked: app.selected = modelData.path
                        onDoubleClicked: modelData.isDir ? app.open(modelData.path) : aura.invoke("files.open_file", "file_item", fr.auraData) }
                }
            }
        }
    }
}
