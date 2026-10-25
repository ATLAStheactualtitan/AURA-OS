"""AURA desktop shell entry point."""
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .engine import Engine
from .ui.bridge import Controller

QML_DIR = Path(__file__).parent / "ui" / "qml"


def build(argv=None, audio=None, engine=None):
    """Create app, engine, controller and QML engine. Returned for tests."""
    argv = list(sys.argv if argv is None else argv)
    app = QGuiApplication.instance() or QGuiApplication(argv)
    QQuickStyle.setStyle("Basic")
    if audio is None:
        try:
            from .apps.audio import AudioEngine
            audio = AudioEngine(app)
        except Exception as e:  # QtMultimedia unavailable: run without audio, honestly reported
            print("Audio disabled:", e, file=sys.stderr)
    eng = engine or Engine(audio=audio)
    ctl = Controller(eng)
    qml = QQmlApplicationEngine()
    qml.rootContext().setContextProperty("aura", ctl)
    qml.rootContext().setContextProperty("fullscreenMode", "--windowed" not in argv)
    qml.addImportPath(str(QML_DIR))
    qml.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    return app, qml, ctl


def main():
    app, qml, ctl = build()
    if not qml.rootObjects():
        print("QML failed to load", file=sys.stderr)
        return 1
    code = app.exec()
    del qml  # destroy QML before the controller it binds to
    return code
