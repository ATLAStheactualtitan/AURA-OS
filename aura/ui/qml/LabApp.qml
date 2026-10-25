import QtQuick
import QtQuick.Controls

// Gesture laboratory: a real right-click playground plus live inspection of what the recogniser sees.
Item {
    id: app
    anchors.fill: parent
    property var g: aura.gesture
    property var last: aura.lastOutcome
    property var hist: aura.history
    property string inspectType: "lab_object"
    property var tree: aura.treeFor(inspectType, { title: "Inspector" })
    onInspectTypeChanged: tree = aura.treeFor(inspectType, { title: "Inspector" })

    Item {
        id: play; width: parent.width * 0.5; height: parent.height
        Text { x: 14; y: 10; text: "Right-click or drag with the right button anywhere here"; color: Theme.dim; font.pixelSize: 11; font.family: Theme.family }
        Rectangle {
            id: panel
            property string auraType: "lab_panel"
            property var auraData: ({ title: "Lab panel" })
            x: 14; y: 36; width: parent.width - 28; height: parent.height - 52; radius: 14
            color: Qt.rgba(1, 1, 1, 0.03); border.color: Theme.border
            Text { x: 12; y: 8; text: "CONTAINER (lab_panel)"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4 }
            Rectangle {
                property string auraType: "lab_object"
                property var auraData: ({ title: "Lab object A" })
                x: 40; y: 60; width: 150; height: 90; radius: 14; color: Qt.rgba(0.49, 0.61, 1, 0.2); border.color: Theme.accent
                Text { anchors.centerIn: parent; text: "Object A"; color: Theme.text; font.family: Theme.family }
            }
            Rectangle {
                property string auraType: "lab_object"
                property var auraData: ({ title: "Lab object B" })
                x: 220; y: 120; width: 150; height: 90; radius: 14; color: Qt.rgba(0.29, 0.84, 0.76, 0.18); border.color: Theme.accent2
                Text { anchors.centerIn: parent; text: "Object B"; color: Theme.text; font.family: Theme.family }
            }
        }
    }

    Rectangle {
        x: play.width; width: parent.width - play.width; height: parent.height; color: Qt.rgba(0, 0, 0, 0.2)
        Flickable {
            anchors.fill: parent; anchors.margins: 12; contentHeight: col.height; clip: true
            Column {
                id: col; width: parent.width; spacing: 8
                Text { text: "RECOGNISER"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4 }
                Text { color: Theme.text; font.family: "monospace"; font.pixelSize: 12; wrapMode: Text.Wrap; width: parent.width
                    text: g.active && g.mode === "gesture"
                        ? "context : " + g.ctxType + " (" + g.ctxLabel + ")\npath    : " + (g.path.length ? g.path.join(" → ") : "—")
                          + "\nnode    : " + g.nodeLabel + "\nready   : " + g.ready + "   paused: " + g.paused
                          + "\nguidance: level " + g.level + " (" + g.detail + ")" + (g.invalid ? "\nINVALID : " + g.invalid : "")
                          + "\nsegments: " + g.segments.map(function (s) { return s.dir + "@" + Math.round(s.t) + "ms" }).join("  ")
                        : "idle" }
                Text { text: "LIVE EVENT LOG"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4; topPadding: 6 }
                Text { color: Theme.text; font.family: "monospace"; font.pixelSize: 11; wrapMode: Text.Wrap; width: parent.width
                    text: g.active && g.log ? g.log.join("\n") : (hist.length ? hist[0].log.join("\n") : "(no gestures yet)") }
                Text { text: "LAST RESULT"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4; topPadding: 6 }
                Text { color: last.ok ? Theme.accent2 : Theme.warn; font.family: "monospace"; font.pixelSize: 12; wrapMode: Text.Wrap; width: parent.width
                    text: last.kind ? last.kind + " · " + last.ctx + "\n" + (last.path || "(no path)") + "\n" + last.duration + " ms total, first segment " + last.first + " ms, "
                          + last.segments + " segment(s)\n→ " + last.message : "—" }
                Text { text: "COMMAND TREE FOR"; color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1.4; topPadding: 6 }
                ComboBox { width: parent.width; model: ["lab_object", "lab_panel", "app:lab", "song", "playlist", "app:music", "folder_item", "file_item", "files_pane", "app:files", "document", "app:editor", "app_icon", "desktop"]
                    onActivated: app.inspectType = currentText }
                Repeater {
                    model: app.tree
                    delegate: Text { required property var modelData
                        x: modelData.depth * 16; font.family: "monospace"; font.pixelSize: 11
                        color: modelData.available ? Theme.famColor(modelData.family) : Theme.dim
                        text: (modelData.available ? "● " : "⊘ ") + modelData.dir + "  " + modelData.label + (modelData.action ? "  [" + modelData.action + "]" : "  (branch)") + (modelData.available ? "" : "  — " + modelData.reason) }
                }
            }
        }
    }
}
