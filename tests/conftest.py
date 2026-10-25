import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aura.engine import Engine  # noqa: E402
from aura.store import Store  # noqa: E402


class FakeAudio:
    def __init__(self):
        self.devs = [dict(id="builtin", name="Built-in Output", default=True), dict(id="spk1", name="Desk Speaker", default=False)]
        self.played = []
        self.playing = False

    def devices(self):
        return self.devs

    def play(self, path, device_id=None, device_name=""):
        if device_id and device_id not in {d["id"] for d in self.devs}:
            return False, f"Output unavailable: {device_name}"
        self.played.append((Path(path).name, device_id))
        return True, f"Playing {Path(path).name} on {device_id or 'default'}"

    def toggle(self):
        return "Paused"

    def stop(self):
        pass


@pytest.fixture
def ui_calls():
    return []


@pytest.fixture
def engine(tmp_path, ui_calls, monkeypatch):
    monkeypatch.setenv("AURA_HOME", str(tmp_path / "home"))
    eng = Engine(store=Store(":memory:"), audio=FakeAudio(), ui=lambda name, **kw: ui_calls.append((name, kw)),
                 workspace=tmp_path / "ws")
    return eng


def drag(session, start, legs, step=5, dt=8.0, t0=1000.0):
    """Drive a session like a real pointer: press, then straight legs of (dx, dy) pixels. Returns the end time."""
    x, y = start
    t = t0
    session.press(x, y, t)
    for dx, dy in legs:
        n = max(1, int(max(abs(dx), abs(dy)) // step))
        for _ in range(n):
            x, y, t = x + dx / n, y + dy / n, t + dt
            session.move(x, y, t)
    return t
