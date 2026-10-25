import QtQuick
import QtQuick.Shapes

// Live gesture overlay: real recognised path, radial options at the current node, command bar.
Item {
    id: ov
    property var g: aura.gesture
    property bool menuMode: g.active && g.mode === "menu"
    property bool gestureMode: g.active && g.mode === "gesture"
    anchors.fill: parent
    visible: g.active

    // --- path ---------------------------------------------------------------
    Canvas {
        id: pathCanvas
        anchors.fill: parent
        visible: ov.gestureMode && g.dragging
        onVisibleChanged: requestPaint()
        Connections { target: aura; function onGestureChanged() { if (ov.gestureMode) pathCanvas.requestPaint() } }
        onPaint: {
            var c = getContext("2d"); c.reset()
            if (!ov.gestureMode || !g.points || g.points.length < 2) return
            var col = g.invalid ? "#ff6b81" : (g.ready ? "#4ad7c1" : "#7c9cff")
            c.lineCap = "round"; c.lineJoin = "round"
            c.strokeStyle = col; c.globalAlpha = 0.18; c.lineWidth = 14
            trace(c)
            c.globalAlpha = 0.95; c.lineWidth = 3.5; trace(c)
            c.globalAlpha = 1; c.fillStyle = col
            c.beginPath(); c.arc(g.press.x, g.press.y, 5, 0, 6.3); c.fill()
            var p = g.points[g.points.length - 1]
            c.beginPath(); c.arc(p.x, p.y, 6, 0, 6.3); c.fillStyle = "#ffffff"; c.fill()
        }
        function trace(c) {
            c.beginPath(); c.moveTo(g.points[0].x, g.points[0].y)
            for (var i = 1; i < g.points.length; i++) c.lineTo(g.points[i].x, g.points[i].y)
            c.stroke()
        }
    }

    // --- node ring ------------------------------------------------------------
    Rectangle {
        visible: ov.gestureMode && g.dragging
        x: (g.node ? g.node.x : 0) - 14; y: (g.node ? g.node.y : 0) - 14; width: 28; height: 28; radius: 14
        color: "transparent"; border.width: 2; border.color: g.ready ? Theme.accent2 : Theme.accent
        Behavior on x { NumberAnimation { duration: 90 } } Behavior on y { NumberAnimation { duration: 90 } }
        Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: parent.border.color }
    }

    // --- options -----------------------------------------------------------------
    Repeater {
        model: ov.gestureMode && g.menuVisible ? g.options : []
        delegate: Rectangle {
            id: pill
            required property var modelData
            property bool compact: g.detail !== "full"
            property bool minimal: g.detail === "minimal"
            property color fam: Theme.famColor(modelData.family)
            property real ring: g.path.length === 0 ? 74 : 58
            width: row.implicitWidth + 26
            height: (minimal ? 34 : 44) + (hintText.visible ? 14 : 0)
            radius: height > 40 ? 16 : height / 2
            x: g.node.x + modelData.dx * (ring + (width / 2)) - width / 2
            y: g.node.y + modelData.dy * (ring + (height / 2)) - height / 2
            color: modelData.highlight ? Qt.rgba(fam.r * 0.5 + 0.05, fam.g * 0.5 + 0.05, fam.b * 0.5 + 0.08, 0.97) : Qt.rgba(0.08, 0.1, 0.16, 0.96)
            border.width: modelData.highlight ? 2.5 : (modelData.recommended ? 2 : 1 + modelData.familiarity * 0.4)
            border.color: !modelData.available ? Qt.rgba(1, 1, 1, 0.12) : (modelData.highlight || modelData.recommended ? fam : Qt.rgba(1, 1, 1, 0.12 + 0.1 * modelData.familiarity))
            opacity: modelData.available ? 1.0 : 0.6
            scale: modelData.highlight ? 1.07 : 1
            Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutBack } }
            Behavior on color { ColorAnimation { duration: 110 } }
            // Entry animation
            property real appear: 0
            Component.onCompleted: appear = 1
            Behavior on appear { NumberAnimation { duration: 140 } }
            transform: Translate { y: (1 - pill.appear) * 6 }

            Row {
                id: row
                anchors.centerIn: parent
                spacing: 8
                Text { text: modelData.arrow; color: modelData.available ? pill.fam : Theme.dim; font.pixelSize: 20; font.family: Theme.family
                       anchors.verticalCenter: parent.verticalCenter }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { id: labelText; text: modelData.label; color: modelData.available ? Theme.text : Theme.dim
                           font.family: Theme.family; font.pixelSize: pill.minimal ? 12 : 14; font.weight: Font.DemiBold
                           font.strikeout: false }
                    Text { visible: !pill.compact && modelData.family !== "" && g.path.length === 0
                           text: modelData.family.toUpperCase(); color: pill.fam; font.pixelSize: 9; font.letterSpacing: 1.4; font.family: Theme.family }
                }
                // Markers: never color-only
                Text { visible: !modelData.available; text: "⊘"; color: Theme.dim; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                Text { visible: modelData.branch && modelData.available; text: "›"; color: Theme.dim; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                Text { visible: modelData.recommended; text: "★"; color: pill.fam; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                Text { visible: modelData.destructive; text: "⚠"; color: Theme.warn; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                Text { visible: !pill.minimal && modelData.familiarity > 0
                       text: ["", "●○○", "●●○", "●●●"][modelData.familiarity]; color: Theme.dim; font.pixelSize: 8; anchors.verticalCenter: parent.verticalCenter }
            }
            Text {
                id: hintText
                visible: !pill.compact && (!modelData.available && modelData.reason !== "")
                text: modelData.reason; color: Theme.dim; font.pixelSize: 10; font.family: Theme.family
                anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 5
            }
        }
    }

    // --- command bar -----------------------------------------------------------
    Rectangle {
        id: bar
        visible: ov.gestureMode && g.dragging && (g.path.length > 0 || g.menuVisible)
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height - 150
        width: Math.min(parent.width - 60, barRow.implicitWidth + 40); height: 48; radius: 24
        color: Theme.glassLight
        border.width: 1.5
        border.color: g.invalid ? Theme.danger : (g.ready ? Theme.accent2 : Theme.border)
        Behavior on border.color { ColorAnimation { duration: 120 } }
        Row {
            id: barRow; anchors.centerIn: parent; spacing: 12
            Text { text: g.invalid ? "⚠" : (g.ready ? "✓" : "…"); font.pixelSize: 16; color: g.invalid ? Theme.danger : (g.ready ? Theme.accent2 : Theme.dim)
                   anchors.verticalCenter: parent.verticalCenter }
            Text { text: g.command || ""; color: Theme.text; font.pixelSize: 14; font.family: Theme.family; font.weight: Font.DemiBold
                   anchors.verticalCenter: parent.verticalCenter }
            Text {
                anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.family: Theme.family
                color: g.invalid ? Theme.danger : (g.ready ? Theme.accent2 : Theme.dim)
                text: g.invalid ? g.invalid + " is not available here — release does nothing"
                    : g.nodeReason ? g.nodeReason
                    : g.ready ? (g.destructive ? "Release to confirm · Esc cancels" : (g.leaf ? "READY — release to execute" : "Release to run · or continue"))
                    : "Incomplete — continue or press Esc"
            }
        }
    }

    // --- contextual menu (plain right-click) ---------------------------------------
    Rectangle {
        id: menu
        visible: ov.menuMode
        property int rows: ov.menuMode ? g.items.length : 0
        width: 330; height: Math.min(ov.height - 20, 54 + rows * 36)
        x: Math.max(10, Math.min(ov.width - width - 10, ov.menuMode ? g.press.x : 0))
        y: Math.max(10, Math.min(ov.height - height - 10, ov.menuMode ? g.press.y : 0))
        radius: Theme.radius + 2; color: Theme.glass; border.color: Theme.border
        scale: visible ? 1 : 0.95
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        Text { x: 16; y: 12; text: ov.menuMode ? g.ctxLabel : ""; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: Theme.family }
        Text { anchors.right: parent.right; anchors.rightMargin: 16; y: 14; text: "gesture shown on the right"; color: Theme.dim; font.pixelSize: 10; font.family: Theme.family }
        ListView {
            anchors.fill: parent; anchors.topMargin: 40; anchors.bottomMargin: 6; clip: true
            model: ov.menuMode ? g.items : []
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width - 12; x: 6; height: 34; radius: 9
                color: ma.containsMouse && modelData.available ? Qt.rgba(1, 1, 1, 0.09) : "transparent"
                Row {
                    x: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                    Text { text: modelData.available ? "●" : "⊘"; font.pixelSize: 8; color: Theme.famColor(modelData.family); anchors.verticalCenter: parent.verticalCenter }
                    Text { text: modelData.label; color: modelData.available ? Theme.text : Theme.dim; font.pixelSize: 13; font.family: Theme.family
                           anchors.verticalCenter: parent.verticalCenter }
                    Text { visible: modelData.destructive; text: "⚠"; color: Theme.warn; font.pixelSize: 12 }
                    Text { visible: modelData.recommended; text: "★"; color: Theme.accent; font.pixelSize: 12 }
                }
                Text { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                       text: modelData.gesture; color: Theme.dim; font.pixelSize: 13 }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton
                            onClicked: aura.menuPick(modelData.index) }
            }
        }
    }
}
