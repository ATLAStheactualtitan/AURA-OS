"""A gesture session binds the recognizer to a context's command tree. No side effects happen here."""
from dataclasses import dataclass, field
from typing import Optional

from .context import Context
from .directions import BY_NAME, CARDINAL, EIGHT_WAY
from .dispatch import Command, command_from_node
from .grammar import FAMILIES, Node
from .recognizer import GestureRecognizer, RecognizerConfig


@dataclass
class Outcome:
    kind: str                       # committed | click | incomplete | invalid | unavailable | cancelled
    command: Optional[Command] = None
    message: str = ""
    path: tuple = ()
    duration_ms: float = 0.0
    first_segment_ms: float = 0.0
    segments: int = 0


class GestureSession:
    def __init__(self, ctx: Context, tree: Node, config: RecognizerConfig = None, familiarity=None):
        self.ctx, self.tree = ctx, tree
        self.rec = GestureRecognizer(config)
        self.familiarity = familiarity or (lambda path: 0)
        self.node = tree
        self.path: list = []
        self.invalid_dir: Optional[str] = None
        self.log: list = []          # (t, kind, text) for the laboratory
        self.points: list = []
        self.t0 = 0.0
        self.finished = False

    # --- input -----------------------------------------------------------
    def press(self, x, y, t):
        self.t0 = t
        self.points = [(x, y)]
        self._log(0.0, "press", f"{self.ctx.type} @ {int(x)},{int(y)}")
        self.rec.press(x, y, t)

    def move(self, x, y, t):
        self.points.append((x, y))
        self._handle(self.rec.move(x, y, t))

    def tick(self, t):
        self._handle(self.rec.tick(t))

    def release(self, t) -> Outcome:
        evs = self.rec.release(t)
        self._handle(evs)
        self.finished = True
        base = dict(path=tuple(self.path), duration_ms=t - self.t0, segments=len(self.rec.segments),
                    first_segment_ms=self.rec.segments[0].t if self.rec.segments else 0.0)
        if any(e.kind == "click" for e in evs):
            o = Outcome("click", message="Contextual menu", **base)
        elif not self.rec.segments:
            o = Outcome("incomplete", message="Gesture too short — nothing happened", **base)
        elif self.invalid_dir:
            o = Outcome("invalid", message=f"{self.invalid_dir} is not available here — nothing happened", **base)
        elif not self.node.available:
            o = Outcome("unavailable", message=self.node.reason or "Unavailable", **base)
        elif not self.node.action_id:
            o = Outcome("incomplete", message="Incomplete gesture — choose a refinement; nothing happened", **base)
        else:
            o = Outcome("committed", command_from_node(self.ctx, self.node), self.command_text, **base)
        self._log(t, "release", o.kind + (f": {o.command.action_id}" if o.command else ""))
        return o

    def cancel(self, t) -> Outcome:
        self.rec.cancel(t)
        self.finished = True
        self._log(t, "cancel", "Escape")
        return Outcome("cancelled", message="Cancelled — nothing happened", path=tuple(self.path),
                       duration_ms=t - self.t0, segments=len(self.rec.segments))

    # --- state for the UI ---------------------------------------------------
    @property
    def dragging(self):
        return self.rec.state.value == "dragging"

    @property
    def paused(self):
        return self.rec.paused

    @property
    def ready(self) -> bool:
        n = self.node
        return bool(self.path) and n.available and bool(n.action_id) and not self.invalid_dir

    @property
    def labels(self) -> list:
        out, n = [], self.tree
        for d in self.path:
            n = n.children[d]
            out.append(n.label if n.family and len(out) else (n.family.title() if n.family else n.label))
        return out

    @property
    def command_text(self) -> str:
        parts = [self.ctx.label]
        if self.path:
            fam = self.tree.children[self.path[0]]
            parts.append(fam.family.upper())
            n = fam
            for d in self.path[1:]:
                n = n.children[d]
                parts.append(n.label)
        return " › ".join(parts)

    def options(self) -> list:
        tent = self.rec.tentative()
        dirs = EIGHT_WAY if not self.path else CARDINAL
        out = []
        for d in dirs:
            c = self.node.children.get(d.name)
            if c is None:
                continue
            key = ">".join(c.path)
            out.append(dict(
                dir=d.name, arrow=d.arrow, dx=d.dx, dy=d.dy, label=c.label, family=c.family,
                hint=c.hint if not self.path else "", available=c.available, reason=c.reason,
                branch=bool(c.children), leaf=bool(c.action_id), destructive=c.destructive,
                recommended=c.recommended, familiarity=self.familiarity(key),
                highlight=bool(tent and tent.name == d.name), path=key,
            ))
        return out

    # --- internals ---------------------------------------------------------
    def _handle(self, events):
        for e in events:
            if e.kind == "segment":
                d = e.segment.direction.name
                child = self.node.children.get(d)
                if child is None or (not self.path and d not in self.tree.children):
                    self.invalid_dir = d
                    self._log(e.t - self.t0, "invalid", d)
                else:
                    self.node, self.invalid_dir = child, None
                    self.path.append(d)
                    self._log(e.t - self.t0, "segment", f"{d} → {child.label}")
            elif e.kind in ("pause", "resume", "drag"):
                self._log(e.t - self.t0, e.kind, "")

    def _log(self, t, kind, text):
        self.log.append((round(t, 1), kind, text))
