import QtQuick
import QtQuick.Controls

Item {
    id: app
    anchors.fill: parent
    property string path: ""
    property bool dirty: false
    property bool loading: false
    property string docName: path ? path.split("/").pop() : "Untitled"

    function newDoc() { loading = true; path = ""; area.text = ""; loading = false; dirty = false; sync() }
    function openPath(p) { loading = true; area.text = aura.readText(p); path = p; loading = false; dirty = false; sync() }
    function sync() { aura.editorState(path, area.text) }
    function findNext(back) {
        var q = findField.text
        if (!q) return
        var t = area.text.toLowerCase(), ql = q.toLowerCase()
        var from = back ? Math.max(0, area.selectionStart - 1) : area.selectionEnd
        var i = back ? t.lastIndexOf(ql, from) : t.indexOf(ql, from)
        if (i < 0) i = back ? t.lastIndexOf(ql) : t.indexOf(ql)
        findInfo.text = i < 0 ? "not found" : ""
        if (i >= 0) { area.select(i, i + q.length); area.forceActiveFocus() }
    }
    Connections {
        target: aura
        function onUiRequest(name, p) {
            if (name === "editor_new") app.newDoc()
            else if (name === "editor_open") app.openPath(p.path)
            else if (name === "editor_saved") { app.path = p.path; app.dirty = false; app.sync() }
            else if (name === "editor_cmd") {
                if (p.cmd === "undo") area.undo()
                else if (p.cmd === "redo") area.redo()
                else if (p.cmd === "focus") area.forceActiveFocus()
                else if (p.cmd === "find") { findBar.visible = true; findField.forceActiveFocus(); findField.selectAll() }
                else if (p.cmd === "upper" || p.cmd === "lower") {
                    var s = area.selectionStart, e = area.selectionEnd
                    if (s === e) { aura.toast("Select text first", false, "warn"); return }
                    var sel = area.selectedText
                    area.remove(s, e)
                    area.insert(s, p.cmd === "upper" ? sel.toUpperCase() : sel.toLowerCase())
                    area.select(s, e)
                }
            }
        }
    }

    Rectangle {
        id: head; width: parent.width; height: 42; color: Qt.rgba(0, 0, 0, 0.18)
        Text { x: 16; anchors.verticalCenter: parent.verticalCenter; color: Theme.text; font.family: Theme.family; font.pixelSize: 13; font.weight: Font.DemiBold
               text: app.docName + (app.dirty ? "  ●" : "") }
        Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; color: Theme.dim; font.pixelSize: 11
               text: app.path || "not saved yet" ; elide: Text.ElideLeft; width: parent.width / 2; horizontalAlignment: Text.AlignRight }
    }
    Rectangle {
        id: findBar; visible: false; y: head.height; width: parent.width; height: visible ? 40 : 0; color: Qt.rgba(1, 0.82, 0.4, 0.1)
        Row { x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            TextField { id: findField; width: 220; height: 28; placeholderText: "Find in document"; color: Theme.text; onAccepted: app.findNext(false)
                background: Rectangle { radius: 14; color: Qt.rgba(1, 1, 1, 0.08); border.color: Theme.border } }
            Button { text: "Next"; onClicked: app.findNext(false) }
            Button { text: "Prev"; onClicked: app.findNext(true) }
            Text { id: findInfo; color: Theme.warn; anchors.verticalCenter: parent.verticalCenter }
            Button { text: "✕"; onClicked: findBar.visible = false }
        }
    }
    Item {
        id: docArea
        property string auraType: "document"
        property var auraData: ({ title: app.docName, path: app.path })
        anchors { left: parent.left; right: parent.right; top: findBar.bottom; bottom: parent.bottom }
        ScrollView {
            anchors.fill: parent; anchors.margins: 6
            TextArea {
                id: area
                color: Theme.text; selectionColor: Theme.accent; selectedTextColor: "#0b0e14"
                font.family: "monospace"; font.pixelSize: 14; wrapMode: TextArea.Wrap
                placeholderText: "Start typing…"; placeholderTextColor: Theme.dim
                background: null
                onTextChanged: { if (!app.loading) { app.dirty = true; app.sync() } }
            }
        }
    }
}
