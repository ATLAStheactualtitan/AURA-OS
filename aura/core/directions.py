"""Direction vocabulary. Screen coordinates: x right, y down. Diagonals are defined but unused by default."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Direction:
    name: str
    dx: float
    dy: float
    arrow: str

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.dy, self.dx))

    def dot(self, other: "Direction") -> float:
        return self.dx * other.dx + self.dy * other.dy


LEFT = Direction("LEFT", -1, 0, "←")
RIGHT = Direction("RIGHT", 1, 0, "→")
UP = Direction("UP", 0, -1, "↑")
DOWN = Direction("DOWN", 0, 1, "↓")
CARDINAL = (LEFT, UP, RIGHT, DOWN)

_s = math.sqrt(0.5)
UP_LEFT = Direction("UP_LEFT", -_s, -_s, "↖")
UP_RIGHT = Direction("UP_RIGHT", _s, -_s, "↗")
DOWN_LEFT = Direction("DOWN_LEFT", -_s, _s, "↙")
DOWN_RIGHT = Direction("DOWN_RIGHT", _s, _s, "↘")
EIGHT_WAY = CARDINAL + (UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT)

BY_NAME = {d.name: d for d in EIGHT_WAY}


def arrows(names) -> str:
    return " ".join(BY_NAME[n].arrow for n in names)


def angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def classify(vx: float, vy: float, directions=CARDINAL, hysteresis_deg: float = 0.0):
    """Return the direction whose sector contains the vector, shrunk by a hysteresis margin; else None."""
    if vx == 0 and vy == 0:
        return None
    a = math.degrees(math.atan2(vy, vx))
    best = min(directions, key=lambda d: angle_diff(a, d.angle))
    half = 180.0 / len(directions)
    margin = min(hysteresis_deg, half * 0.9)
    return best if angle_diff(a, best.angle) <= half - margin else None
