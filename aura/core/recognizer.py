"""Pointer-driven multi-segment gesture recognizer. Pure Python; time is injected (milliseconds)."""
import math
from dataclasses import dataclass, field
from enum import Enum

from .directions import CARDINAL, EIGHT_WAY, Direction, classify


class State(Enum):
    IDLE = "idle"
    PRESSED = "pressed"
    DRAGGING = "dragging"


@dataclass
class RecognizerConfig:
    drag_px: float = 8.0          # movement before a press becomes a drag
    segment_px: float = 40.0      # length needed to recognise the first direction
    turn_px: float = 40.0         # distance from the segment's peak needed to turn
    reverse_factor: float = 1.5   # extra distance required for a 180-degree reversal
    hysteresis_deg: float = 10.0  # sector shrink: ambiguous diagonals are ignored
    pause_ms: float = 350.0
    jitter_px: float = 3.0
    directions: tuple = CARDINAL          # directions for every segment after the first
    first_directions: tuple = EIGHT_WAY   # root level carries the seven action families


@dataclass
class Segment:
    direction: Direction
    origin: tuple
    t: float                      # ms since press when recognised
    end: tuple = None


@dataclass
class Event:
    kind: str                     # press|drag|segment|pause|resume|release|click|cancel
    t: float
    pos: tuple
    segment: Segment = None


class GestureRecognizer:
    def __init__(self, config: RecognizerConfig = None):
        self.config = config or RecognizerConfig()
        self.state = State.IDLE
        self.segments: list = []
        self.paused = False
        self.pos = (0.0, 0.0)
        self.anchor = self.peak = self.start = self.last_pos = (0.0, 0.0)
        self.cur = None
        self.peak_ext = 0.0
        self.t0 = self.last_move_t = 0.0

    # --- input ---------------------------------------------------------
    def press(self, x, y, t):
        self.state = State.PRESSED
        self.segments = []
        self.paused = False
        self.start = self.anchor = self.peak = self.last_pos = self.pos = (x, y)
        self.cur = None
        self.peak_ext = 0.0
        self.t0 = self.last_move_t = t
        return [Event("press", t, (x, y))]

    def move(self, x, y, t):
        if self.state is State.IDLE:
            return []
        ev = []
        c = self.config
        if math.hypot(x - self.last_pos[0], y - self.last_pos[1]) >= c.jitter_px:
            self.last_pos = (x, y)
            self.last_move_t = t
            if self.paused:
                self.paused = False
                ev.append(Event("resume", t, (x, y)))
        self.pos = (x, y)
        if self.state is State.PRESSED:
            if math.hypot(x - self.start[0], y - self.start[1]) < c.drag_px:
                return ev
            self.state = State.DRAGGING
            ev.append(Event("drag", t, (x, y)))
        self._track(x, y, t, ev)
        return ev

    def tick(self, t):
        if self.state is State.DRAGGING and not self.paused and t - self.last_move_t >= self.config.pause_ms:
            self.paused = True
            return [Event("pause", t, self.pos)]
        return []

    def release(self, t):
        prev, self.state = self.state, State.IDLE
        if prev is State.IDLE:
            return []
        if prev is State.PRESSED:
            return [Event("click", t, self.pos)]
        if self.segments:
            self.segments[-1].end = self.peak
        return [Event("release", t, self.pos)]

    def cancel(self, t):
        prev, self.state = self.state, State.IDLE
        return [Event("cancel", t, self.pos)] if prev is not State.IDLE else []

    # --- live feedback -------------------------------------------------
    def tentative(self):
        """Direction the pointer is heading toward before it is committed."""
        if self.state is not State.DRAGGING:
            return None
        ref = self.anchor if self.cur is None else self.peak
        vx, vy = self.pos[0] - ref[0], self.pos[1] - ref[1]
        if math.hypot(vx, vy) < 12:
            return None
        dirs = self.config.first_directions if self.cur is None else self.config.directions
        d = classify(vx, vy, dirs, self.config.hysteresis_deg)
        return d if d is not self.cur else None

    # --- internals -----------------------------------------------------
    def _track(self, x, y, t, ev):
        c = self.config
        if self.cur is None:
            vx, vy = x - self.anchor[0], y - self.anchor[1]
            if math.hypot(vx, vy) >= c.segment_px:
                d = classify(vx, vy, c.first_directions, c.hysteresis_deg)
                if d:
                    self._begin(d, self.anchor, (x, y), t, ev)
            return
        cur = self.cur
        ext = (x - self.anchor[0]) * cur.dx + (y - self.anchor[1]) * cur.dy
        if ext > self.peak_ext:
            self.peak, self.peak_ext = (x, y), ext
            return
        wx, wy = x - self.peak[0], y - self.peak[1]
        dist = math.hypot(wx, wy)
        if dist < c.turn_px:
            return
        nd = classify(wx, wy, c.directions, c.hysteresis_deg)
        if nd is None or nd is cur:
            return
        need = c.turn_px * (c.reverse_factor if nd.dot(cur) < -0.5 else 1.0)
        if dist >= need:
            self._begin(nd, self.peak, (x, y), t, ev)

    def _begin(self, d, origin, p, t, ev):
        if self.segments:
            self.segments[-1].end = origin
        self.anchor, self.cur = origin, d
        self.peak = p
        self.peak_ext = (p[0] - origin[0]) * d.dx + (p[1] - origin[1]) * d.dy
        seg = Segment(d, origin, t - self.t0)
        self.segments.append(seg)
        self.paused = False
        ev.append(Event("segment", t, p, seg))
