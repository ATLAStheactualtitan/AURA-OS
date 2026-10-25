import QtQuick
import QtQuick.Controls

Item {
    id: app
    anchors.fill: parent
    property var s: aura.settings()
    function refresh() { s = aura.settings() }
    Connections { target: aura; function onSettingsChanged() { app.refresh() } }
    onVisibleChanged: if (visible) refresh()

    Flickable {
        anchors.fill: parent; anchors.margins: 18; contentHeight: col.height; clip: true
        Column {
            id: col; width: parent.width; spacing: 10
            Text { text: "Adaptive guidance"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: Theme.family }
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.pixelSize: 12; font.family: Theme.family
                   text: "Adaptation only changes how much visual guidance is shown. It never moves or remaps a gesture." }
            Switch { text: "Adapt guidance to my proficiency"; checked: s.adaptation; onToggled: aura.setAdaptation(checked)
                     contentItem: Text { text: parent.text; leftPadding: 50; color: Theme.text; verticalAlignment: Text.AlignVCenter } }
            Text { color: Theme.accent2; font.pixelSize: 14; font.family: Theme.family
                   text: "Level " + s.guidance.level + " — " + s.guidance.name + "  (menu delay " + s.guidance.menu_delay_ms + " ms, " + s.guidance.detail + " labels)" }
            Text { color: Theme.text; font.family: "monospace"; font.pixelSize: 12
                   text: "gestures attempted : " + s.stats.attempts + "\nsuccessful         : " + s.stats.successes + "\ncancelled          : " + s.stats.cancelled
                       + "\nerrors/incomplete  : " + s.stats.errors + "\nrecent success rate: " + Math.round(s.stats.recent_rate * 100) + "%\nmedian time (ms)   : " + Math.round(s.stats.median_ms)
                       + "\nmenu selections    : " + s.stats.menu_uses }
            Row { spacing: 8
                Button { text: "Restore full guidance"; onClicked: aura.restoreGuidance() }
                Button { text: "Reset proficiency data"; onClicked: aura.resetProficiency() }
            }
            Text { text: "Gesture mapping (stable)"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold; topPadding: 12 }
            Repeater { model: Object.keys(s.familyMap)
                delegate: Text { required property string modelData; color: Theme.famColor(s.familyMap[modelData].charAt(0) + s.familyMap[modelData].slice(1).toLowerCase()); font.family: "monospace"; font.pixelSize: 13
                    text: modelData.padEnd(10) + " →  " + s.familyMap[modelData] } }
            Text { text: "Recogniser thresholds (px / ms / degrees)"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold; topPadding: 12 }
            Repeater { model: ["drag_px", "segment_px", "turn_px", "hysteresis_deg"]
                delegate: Row { required property string modelData; spacing: 10
                    Text { width: 130; text: modelData; color: Theme.text; font.family: "monospace"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    Slider { width: 220; from: modelData === "hysteresis_deg" ? 0 : 4; to: modelData === "hysteresis_deg" ? 20 : 120; value: s.recognizer[modelData]
                             onMoved: aura.setThreshold(modelData, value) }
                    Text { text: Math.round(s.recognizer[modelData]); color: Theme.dim; anchors.verticalCenter: parent.verticalCenter } } }
            Text { text: "Audio server"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold; topPadding: 12 }
            Button { text: "Show WirePlumber status"; onClicked: pw.text = aura.pipewire() }
            Text { id: pw; width: parent.width; wrapMode: Text.Wrap; color: Theme.dim; font.family: "monospace"; font.pixelSize: 10 }
        }
    }
}
