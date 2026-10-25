pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#000000"
    readonly property color surface: "#1c1c1e"
    readonly property color surface2: "#2c2c2e"
    readonly property color glass: Qt.rgba(0.17, 0.17, 0.18, 0.78)
    readonly property color glassLight: Qt.rgba(0.22, 0.22, 0.23, 0.9)
    readonly property color border: Qt.rgba(1, 1, 1, 0.12)
    readonly property color accent: "#0a84ff"
    readonly property color accent2: "#30d158"
    readonly property color warn: "#ff9f0a"
    readonly property color danger: "#ff453a"
    readonly property color text: "#f5f5f7"
    readonly property color dim: "#98989d"
    readonly property int radius: 12
    readonly property string family: {
        var f = Qt.fontFamilies()
        var pref = [".AppleSystemUIFont", "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Inter"]
        for (var i = 0; i < pref.length; i++)
            if (f.indexOf(pref[i]) >= 0) return pref[i]
        return Qt.application.font.family
    }
    readonly property var familyColors: ({
        "Act": "#0a84ff", "Preserve": "#30d158", "Find": "#ffd60a", "Organize": "#bf5af2",
        "Modify": "#ff9f0a", "Navigate": "#64d2ff", "Reverse": "#ff453a"
    })
    function famColor(f) { return familyColors[f] || accent }
}
