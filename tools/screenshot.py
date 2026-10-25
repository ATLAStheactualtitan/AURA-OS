"""Render the shell offscreen with a gesture in progress and save PNGs (visual check)."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "tests"); sys.path.insert(0, ".")
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from aura.app import build
from test_e2e_ui import send, right_gesture, song_pos, Qt
from conftest import FakeAudio

app, qml, ctl = build(["aura", "--windowed"], audio=FakeAudio())
win = qml.rootObjects()[0]; win.resize(1280, 800); win.show()
ctl.uiRequest.emit("open_app", {"app": "music"}); QTest.qWait(400)
ctl.engine.store.assign("music.output", "RIGHT", "spk1", "Desk Speaker")
x, y = right_gesture(win, song_pos(win), [(-90, 0), (0, 90)], release=False)
QTest.qWait(200); win.grabWindow().save("/tmp/aura_gesture.png")
send(win, QEvent.MouseButtonRelease, x, y, Qt.RightButton, Qt.NoButton)
ctl.uiRequest.emit("open_app", {"app": "lab"}); QTest.qWait(300)
x, y = song_pos(win)
right_gesture(win, (300, 500), [(0, 80)], release=True)
QTest.qWait(200); win.grabWindow().save("/tmp/aura_lab.png")
print("saved")
