import pytest

from aura.core.directions import CARDINAL, EIGHT_WAY, classify
from aura.core.grammar import DEFAULT_FAMILY_MAP, GrammarError, validate_family_map
from aura.core.recognizer import GestureRecognizer, RecognizerConfig

from conftest import drag


def run(legs, cfg=None, step=5):
    r = GestureRecognizer(cfg)
    x, y, t = 100.0, 100.0, 0.0
    r.press(x, y, t)
    evs = []
    for dx, dy in legs:
        n = max(1, int(max(abs(dx), abs(dy)) // step))
        for _ in range(n):
            x, y, t = x + dx / n, y + dy / n, t + 8
            evs += r.move(x, y, t)
    evs += r.release(t + 8)
    return r, [e.segment.direction.name for e in evs if e.kind == "segment"], evs


@pytest.mark.parametrize("leg,name", [((-80, 0), "LEFT"), ((80, 0), "RIGHT"), ((0, -80), "UP"), ((0, 80), "DOWN")])
def test_cardinal_directions(leg, name):
    _, segs, _ = run([leg])
    assert segs == [name]


def test_diagonal_first_segment_and_extensible():
    _, segs, _ = run([(60, -60)])
    assert segs == ["UP_RIGHT"]
    assert classify(-1, 0, EIGHT_WAY).name == "LEFT" and classify(1, 1, EIGHT_WAY).name == "DOWN_RIGHT"
    assert classify(1, 1, CARDINAL, hysteresis_deg=10) is None  # ambiguous on four-way input


def test_left_down_right():
    _, segs, _ = run([(-80, 0), (0, 80), (80, 0)])
    assert segs == ["LEFT", "DOWN", "RIGHT"]


def test_four_segments():
    _, segs, _ = run([(-80, 0), (0, 80), (80, 0), (0, -80)])
    assert segs == ["LEFT", "DOWN", "RIGHT", "UP"]


def test_no_repeat_along_same_segment():
    _, segs, _ = run([(-400, 0)])
    assert segs == ["LEFT"]


def test_small_wobble_does_not_turn():
    _, segs, _ = run([(-80, 0), (0, 15), (0, -10), (-40, 0)])
    assert segs == ["LEFT"]


def test_reversal_needs_extra_distance():
    _, segs, _ = run([(-80, 0), (50, 0)])           # 50 < 40 * 1.5
    assert segs == ["LEFT"]
    _, segs, _ = run([(-80, 0), (70, 0)])
    assert segs == ["LEFT", "RIGHT"]


def test_click_without_drag():
    r = GestureRecognizer()
    r.press(10, 10, 0)
    r.move(12, 11, 5)
    assert [e.kind for e in r.release(10)] == ["click"]


def test_pause_and_resume():
    r = GestureRecognizer(RecognizerConfig(pause_ms=300))
    r.press(0, 0, 0)
    r.move(-60, 0, 100)
    assert r.tick(200) == []
    assert [e.kind for e in r.tick(500)] == ["pause"]
    assert [e.kind for e in r.move(-90, 0, 600)] == ["resume"]


def test_cancel():
    r = GestureRecognizer()
    r.press(0, 0, 0)
    r.move(-60, 0, 100)
    assert [e.kind for e in r.cancel(120)] == ["cancel"]
    assert r.release(130) == []


def test_family_map_validation():
    validate_family_map(DEFAULT_FAMILY_MAP)
    with pytest.raises(GrammarError):
        validate_family_map({"LEFT": "ACT", "UP": "ACT"})
