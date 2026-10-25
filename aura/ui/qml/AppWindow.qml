import QtQuick
import QtQuick.Controls

// A draggable shell window. Children go into the content area.
Rectangle {
    id: win
    property string title: ""
    property string appId: ""
    property string auraType: "app:" + appId
    property var auraData: ({})
    property color tint: Theme.accent
    default property alias content: body.data
    signal raised()
    signal closed()
    width: 760; height: 520
    x: 140; y: 70
    radius: 12
    color: Qt.rgba(0.12, 0.12, 0.13, 0.98)
    border.color: focus || activeFocus ? Qt.rgba(1, 1, 1, 0.2) : Theme.border
    visible: false
    opacity: visible ? 1 : 0
    scale: visible ? 1 : 0.96
    Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    clip: true

    function open() { visible = true; raised() }

    Rectangle {
        id: bar
        width: parent.width; height: 40
        color: Qt.rgba(1, 1, 1, 0.06)
        Rectangle { width: parent.width; height: 1; anchors.bottom: parent.bottom; color: Qt.rgba(0, 0, 0, 0.5) }
        Row {
            x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            Rectangle {
                width: 12; height: 12; radius: 6; color: "#ff5f57"
                MouseArea { anchors.fill: parent; onClicked: { win.visible = false; win.closed() } }
            }
            Rectangle { width: 12; height: 12; radius: 6; color: "#febc2e" }
            Rectangle { width: 12; height: 12; radius: 6; color: "#28c840" }
        }
        Text {
            anchors.centerIn: parent
            text: win.title; color: Theme.text; font.family: Theme.family; font.pixelSize: 13; font.weight: Font.DemiBold
        }
        MouseArea {
            anchors.fill: parent; acceptedButtons: Qt.LeftButton
            drag.target: win; drag.minimumX: -win.width + 120; drag.minimumY: 0
            onPressed: win.raised()
        }
    }
    Item { id: body; y: bar.height; width: parent.width; height: parent.height - bar.height }

    Rectangle {  // resize grip
        width: 18; height: 18; anchors.right: parent.right; anchors.bottom: parent.bottom; color: "transparent"
        Text { anchors.centerIn: parent; text: "◢"; color: Theme.dim; font.pixelSize: 10 }
        MouseArea {
            anchors.fill: parent; acceptedButtons: Qt.LeftButton; cursorShape: Qt.SizeFDiagCursor
            property real sx; property real sy; property real sw; property real sh
            onPressed: (m) => { var p = mapToItem(null, m.x, m.y); sx = p.x; sy = p.y; sw = win.width; sh = win.height }
            onPositionChanged: (m) => { if (!pressed) return; var p = mapToItem(null, m.x, m.y)
                win.width = Math.max(420, sw + p.x - sx); win.height = Math.max(300, sh + p.y - sy) }
        }
    }
}
