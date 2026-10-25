import QtQuick
import QtQuick.Controls

// A draggable shell window. Children go into the content area.
Item {
    id: win
    property string title: ""
    property string appId: ""
    property string auraType: "app:" + appId
    property var auraData: ({})
    property color tint: Theme.accent
    property bool maximized: false
    property bool animate: false
    property rect restore: Qt.rect(0, 0, 0, 0)
    default property alias content: body.data
    signal raised()
    signal closed()
    width: 760; height: 520
    x: 140; y: 70
    visible: false
    opacity: visible ? 1 : 0
    scale: visible ? 1 : 0.95
    transformOrigin: Item.Bottom
    Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Behavior on x { enabled: win.animate; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on y { enabled: win.animate; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on width { enabled: win.animate; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on height { enabled: win.animate; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Timer { id: settle; interval: 280; onTriggered: win.animate = false }

    function open() { visible = true; raised() }
    function toggleMaximize() {
        animate = true; settle.restart()
        if (maximized) { x = restore.x; y = restore.y; width = restore.width; height = restore.height; maximized = false }
        else {
            restore = Qt.rect(x, y, width, height)
            x = 12; y = Theme.menuBar + 6; width = parent.width - 24; height = parent.height - Theme.menuBar - Theme.dockReserve - 6
            maximized = true
        }
        raised()
    }
    function minimize() { visible = false }
    function close() { if (maximized) { x = restore.x; y = restore.y; width = restore.width; height = restore.height; maximized = false } visible = false; closed() }

    Item {  // soft layered shadow
        anchors.fill: parent
        Repeater {
            model: 5
            Rectangle {
                required property int index
                x: -index * 6; y: 8 - index * 4; width: win.width + index * 12; height: win.height + index * 12
                radius: 18 + index * 6; color: "#000000"; opacity: 0.07
            }
        }
    }

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: 16
        clip: true
        color: Theme.surface
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.1)

        Rectangle {
            id: bar
            width: parent.width; height: 48
            color: Qt.rgba(1, 1, 1, 0.035)
            Rectangle { width: parent.width; height: 1; anchors.bottom: parent.bottom; color: Qt.rgba(1, 1, 1, 0.07) }
            MouseArea {
                anchors.fill: parent; acceptedButtons: Qt.LeftButton
                drag.target: win.maximized ? null : win; drag.minimumX: -win.width + 120; drag.minimumY: Theme.menuBar
                onPressed: win.raised()
                onDoubleClicked: win.toggleMaximize()
            }
            Rectangle {
                x: 18; anchors.verticalCenter: parent.verticalCenter; width: 8; height: 8; radius: 4; color: win.tint
            }
            Text {
                x: 36; anchors.verticalCenter: parent.verticalCenter
                text: win.title; color: Theme.text; font.family: Theme.family; font.pixelSize: 14; font.weight: Font.DemiBold
            }
            // The only window control: right-click and drag from here.
            Rectangle {
                id: ctl
                property string auraType: "window_control"
                property var auraData: ({ app: win.appId })
                anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter
                width: 78; height: 28; radius: 14
                color: Qt.rgba(1, 1, 1, 0.07); border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.1)
                Text { anchors.centerIn: parent; text: "↑   ↓   →"; color: Theme.dim; font.family: Theme.family; font.pixelSize: 12 }
            }
        }
        Item { id: body; y: bar.height; width: parent.width; height: parent.height - bar.height }

        Item {  // resize grip
            width: 22; height: 22; anchors.right: parent.right; anchors.bottom: parent.bottom; visible: !win.maximized
            Text { anchors.centerIn: parent; text: "◢"; color: Theme.dim; opacity: 0.5; font.pixelSize: 9 }
            MouseArea {
                anchors.fill: parent; acceptedButtons: Qt.LeftButton; cursorShape: Qt.SizeFDiagCursor
                property real sx; property real sy; property real sw; property real sh
                onPressed: (m) => { var p = mapToItem(null, m.x, m.y); sx = p.x; sy = p.y; sw = win.width; sh = win.height }
                onPositionChanged: (m) => { if (!pressed) return; var p = mapToItem(null, m.x, m.y)
                    win.width = Math.max(420, sw + p.x - sx); win.height = Math.max(300, sh + p.y - sy) }
            }
        }
    }
}
