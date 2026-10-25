"""Headless smoke check: load the QML shell and exit."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
from PySide6.QtCore import QTimer
from aura.app import build

app, qml, ctl = build(["aura", "--windowed"])
print("root objects:", len(qml.rootObjects()))
QTimer.singleShot(1500, app.quit)
app.exec()
sys.exit(0 if qml.rootObjects() else 1)
