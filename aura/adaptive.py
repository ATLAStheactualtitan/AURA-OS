"""Interpretable proficiency model: plain counters and thresholds, no learning magic.

Level 0 full guidance .. level 3 fluent. Adaptation only changes *visual guidance*; it never
moves or remaps a gesture.
"""
import statistics
import time

GUIDANCE = {
    0: dict(name="Guided", menu_delay_ms=0, detail="full"),
    1: dict(name="Assisted", menu_delay_ms=250, detail="full"),
    2: dict(name="Compact", menu_delay_ms=550, detail="compact"),
    3: dict(name="Fluent", menu_delay_ms=900, detail="minimal"),
}
GESTURE_OUTCOMES = ("committed", "invalid", "unavailable", "incomplete", "cancelled")


class Proficiency:
    def __init__(self, store):
        self.store = store

    @property
    def enabled(self) -> bool:
        return bool(self.store.get("adaptation_enabled", True))

    @property
    def since(self) -> float:
        return float(self.store.get("adaptive_since", 0.0))

    def _rows(self, limit=None):
        return [r for r in self.store.interactions(self.since, limit) if r["via"] == "gesture" and r["outcome"] in GESTURE_OUTCOMES]

    def stats(self) -> dict:
        rows = self._rows()
        recent = rows[:30]
        ok = [r for r in rows if r["outcome"] == "committed"]
        times = [r["duration_ms"] for r in ok[:20] if r["duration_ms"]]
        return dict(
            attempts=len(rows), successes=len(ok),
            cancelled=sum(r["outcome"] == "cancelled" for r in rows),
            errors=sum(r["outcome"] in ("invalid", "unavailable", "incomplete") for r in rows),
            recent_rate=(sum(r["outcome"] == "committed" for r in recent) / len(recent)) if recent else 0.0,
            median_ms=statistics.median(times) if times else 0.0,
            menu_uses=sum(1 for r in self.store.interactions(self.since) if r["via"] == "menu"),
        )

    def level(self) -> int:
        if not self.enabled:
            return 0
        s = self.stats()
        n, rate = s["successes"], s["recent_rate"]
        if n < 5:
            return 0
        if n < 15 or rate < 0.7:
            return 1
        if n < 40 or rate < 0.8:
            return 2
        return 3

    def guidance(self) -> dict:
        lv = self.level()
        g = dict(GUIDANCE[lv], level=lv, enabled=self.enabled)
        return g

    def familiarity(self, path_key: str) -> int:
        """0 new, 1 seen, 2 practiced, 3 fluent — per gesture path (not per context)."""
        if not self.enabled:
            return 0
        n = sum(1 for r in self._rows() if r["outcome"] == "committed" and r["path"] == path_key)
        return 0 if n == 0 else 1 if n < 3 else 2 if n < 8 else 3

    def suggestion(self, path_key: str, action: str):
        """Offer the gesture shortcut after the same action was chosen from the menu 3+ times."""
        if not self.enabled or not path_key:
            return None
        menu = sum(1 for r in self.store.interactions(self.since) if r["via"] == "menu" and r["path"] == path_key)
        if menu >= 3 and self.familiarity(path_key) < 2:
            return f"Tip: {path_key.replace('>', ' → ')} runs “{action}” without the menu."
        return None

    def restore_full_guidance(self):
        """Keep the data but start the model from scratch."""
        self.store.set("adaptive_since", time.time())

    def reset(self):
        self.store.reset_interactions()
        self.store.set("adaptive_since", 0.0)
