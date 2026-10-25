from aura.adaptive import Proficiency
from aura.store import Store


def log(store, n, outcome="committed", path="LEFT", via="gesture", ms=800):
    for _ in range(n):
        store.log_interaction("song", path, "x", outcome, ms, 100, 1, via)


def test_starts_fully_guided():
    p = Proficiency(Store(":memory:"))
    assert p.level() == 0 and p.guidance()["menu_delay_ms"] == 0


def test_levels_progress_with_success():
    s = Store(":memory:")
    p = Proficiency(s)
    log(s, 6)
    assert p.level() == 1
    log(s, 10)
    assert p.level() == 2
    log(s, 30)
    assert p.level() == 3 and p.guidance()["detail"] == "minimal"


def test_errors_lower_the_level():
    s = Store(":memory:")
    p = Proficiency(s)
    log(s, 50)
    assert p.level() == 3
    log(s, 30, "invalid")
    assert p.level() < 3
    st = p.stats()
    assert st["errors"] == 30 and st["successes"] == 50 and st["median_ms"] == 800


def test_cancellations_counted():
    s = Store(":memory:")
    log(s, 2, "cancelled")
    assert Proficiency(s).stats()["cancelled"] == 2


def test_familiarity_per_path():
    s = Store(":memory:")
    p = Proficiency(s)
    assert p.familiarity("LEFT>DOWN") == 0
    log(s, 1, path="LEFT>DOWN")
    assert p.familiarity("LEFT>DOWN") == 1
    log(s, 8, path="LEFT>DOWN")
    assert p.familiarity("LEFT>DOWN") == 3


def test_disable_reset_restore():
    s = Store(":memory:")
    p = Proficiency(s)
    log(s, 50)
    s.set("adaptation_enabled", False)
    assert p.level() == 0 and p.familiarity("LEFT") == 0
    s.set("adaptation_enabled", True)
    assert p.level() == 3
    p.restore_full_guidance()
    assert p.level() == 0 and len(s.interactions()) == 50
    p.reset()
    assert s.interactions() == []


def test_accelerator_suggestion_after_menu_use():
    s = Store(":memory:")
    p = Proficiency(s)
    log(s, 2, via="menu", path="LEFT>DOWN")
    assert p.suggestion("LEFT>DOWN", "Choose output") is None
    log(s, 1, via="menu", path="LEFT>DOWN")
    assert "LEFT → DOWN" in p.suggestion("LEFT>DOWN", "Choose output")


def test_adaptation_never_changes_mappings(engine):
    before = dict(engine.family_map)
    for _ in range(60):
        engine.store.log_interaction("song", "LEFT", "music.play", "committed")
    assert engine.family_map == before
    t1 = [o["dir"] for o in __import__("aura.core.session", fromlist=["x"]).GestureSession(
        engine.context("song"), engine.tree(engine.context("song"))).options()]
    assert t1 == [o["dir"] for o in __import__("aura.core.session", fromlist=["x"]).GestureSession(
        engine.context("song"), engine.tree(engine.context("song")), familiarity=engine.prof.familiarity).options()]
