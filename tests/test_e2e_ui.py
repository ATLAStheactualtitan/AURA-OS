"""End-to-end: real mouse events delivered to the QML window drive the real recogniser, overlay state and dispatcher."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from conftest import FakeAudio

pytestmark = pytest.mark.filterwarnings("ignore")


def send(win, kind, x, y, button, buttons):
    p = QPointF(x, y)
    QCoreApplication.sendEvent(win, QMouseEvent(kind, p, p, button, buttons, Qt.NoModifier))
    QCoreApplication.processEvents()


def right_gesture(win, start, legs, release=True, step=6):
    x, y = start
    send(win, QEvent.MouseButtonPress, x, y, Qt.RightButton, Qt.RightButton)
    for dx, dy in legs:
        n = max(1, int(max(abs(dx), abs(dy)) // step))
        for _ in range(n):
            x, y = x + dx / n, y + dy / n
            send(win, QEvent.MouseMove, x, y, Qt.NoButton, Qt.RightButton)
    if release:
        send(win, QEvent.MouseButtonRelease, x, y, Qt.RightButton, Qt.NoButton)
    return x, y


@pytest.fixture
def shell(tmp_path, monkeypatch):
    monkeypatch.setenv("AURA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AURA_WORKSPACE", str(tmp_path / "ws"))
    from aura.app import build
    audio = FakeAudio()
    app, qml, ctl = build(["aura", "--windowed"], audio=audio)
    win = qml.rootObjects()[0]
    win.resize(1300, 850)
    win.show()
    QCoreApplication.processEvents()
    ctl.uiRequest.emit("open_app", {"app": "music"})
    QTest.qWait(300)
    toasts = []
    ctl.toast.connect(lambda t, ok, k: toasts.append((t, ok, k)))
    yield win, ctl, audio, toasts
    win.close()


def find_item(item, name):
    if item.objectName() == name:
        return item
    for c in item.childItems():
        r = find_item(c, name)
        if r:
            return r
    return None


def song_pos(win):
    item = find_item(win.contentItem(), "song-0")
    assert item is not None, "song delegate not found"
    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return p.x(), p.y()


def test_left_down_right_plays_on_assigned_speaker(shell):
    win, ctl, audio, toasts = shell
    ctl.engine.store.assign("music.output", "RIGHT", "spk1", "Desk Speaker")
    start = song_pos(win)
    x, y = right_gesture(win, start, [(-90, 0), (0, 90), (90, 0)], release=False)
    g = ctl.gesture
    assert g["active"] and g["path"] == ["LEFT", "DOWN", "RIGHT"] and g["ready"] and g["ctxType"] == "song"
    assert audio.played == []                                   # nothing before release
    send(win, QEvent.MouseButtonRelease, x, y, Qt.RightButton, Qt.NoButton)
    assert audio.played and audio.played[-1][1] == "spk1"
    assert toasts[-1][1] and "spk1" in toasts[-1][0]
    assert ctl.lastOutcome["kind"] == "committed" and ctl.lastOutcome["path"] == "LEFT → DOWN → RIGHT"


def test_escape_cancels_without_side_effects(shell):
    win, ctl, audio, _ = shell
    x, y = right_gesture(win, song_pos(win), [(-90, 0)], release=False)
    assert ctl.gesture["active"]
    ctl.cancelGesture()
    send(win, QEvent.MouseButtonRelease, x, y, Qt.RightButton, Qt.NoButton)
    assert audio.played == [] and ctl.engine.store.interactions()[0]["outcome"] == "cancelled"


def test_right_click_opens_contextual_menu_and_executes(shell):
    win, ctl, audio, _ = shell
    x, y = song_pos(win)
    send(win, QEvent.MouseButtonPress, x, y, Qt.RightButton, Qt.RightButton)
    send(win, QEvent.MouseButtonRelease, x, y, Qt.RightButton, Qt.NoButton)
    g = ctl.gesture
    assert g["mode"] == "menu" and any(i["label"] == "Play" for i in g["items"])
    ctl.menuPick(next(i["index"] for i in g["items"] if i["label"] == "Play"))
    assert audio.played


def test_overlay_options_reveal_second_level(shell):
    win, ctl, _, _ = shell
    right_gesture(win, song_pos(win), [(-90, 0)], release=False)
    opts = {o["dir"]: o for o in ctl.gesture["options"]}
    assert set(opts) == {"DOWN"}                            # only refinement under ACT on a song
    assert opts["DOWN"]["label"] == "Choose output"
    send(win, QEvent.MouseButtonRelease, 0, 0, Qt.RightButton, Qt.NoButton)
