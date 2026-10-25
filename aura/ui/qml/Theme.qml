pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#07060f"
    readonly property color surface: "#13121f"
    readonly property color surface2: "#1d1b2e"
    readonly property color glass: Qt.rgba(0.1, 0.09, 0.17, 0.72)
    readonly property color glassLight: Qt.rgba(0.13, 0.12, 0.22, 0.94)
    readonly property color border: Qt.rgba(1, 1, 1, 0.09)
    readonly property color accent: "#8b7bff"
    readonly property color accent2: "#3de0b0"
    readonly property color warn: "#ffb24a"
    readonly property color danger: "#ff5d7a"
    readonly property color text: "#f3f2fb"
    readonly property color dim: "#9391ad"
    readonly property int radius: 16
    readonly property int menuBar: 36
    readonly property int dockReserve: 104
    readonly property string family: {
        var f = Qt.fontFamilies()
        var pref = [".AppleSystemUIFont", "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Inter"]
        for (var i = 0; i < pref.length; i++)
            if (f.indexOf(pref[i]) >= 0) return pref[i]
        return Qt.application.font.family
    }
    readonly property var familyColors: ({
        "Act": "#8b7bff", "Preserve": "#3de0b0", "Find": "#ffd86b", "Organize": "#d68bff",
        "Modify": "#ffa35c", "Navigate": "#6cd0ff", "Reverse": "#ff6f8d"
    })
    function famColor(f) { return familyColors[f] || accent }
}
