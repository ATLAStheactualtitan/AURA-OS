"""Benchmarks: recogniser throughput, tree building, and full command resolution latency.

    .venv/bin/python -m tools.benchmark
"""
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from aura.engine import Engine  # noqa: E402
from aura.store import Store  # noqa: E402
from conftest import FakeAudio, drag  # noqa: E402


def timed(fn, n):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    return statistics.median(xs), max(xs)


def main():
    with tempfile.TemporaryDirectory() as d:
        eng = Engine(store=Store(":memory:"), audio=FakeAudio(), workspace=Path(d) / "ws")
        eng.store.assign("music.output", "RIGHT", "spk1", "Desk Speaker")
        ctx = eng.context("song", dict(path=eng.library.tracks[0]["path"], title="t", artist="a"))
        print(f"{'benchmark':44s} {'median ms':>10s} {'worst ms':>10s}")
        m, w = timed(lambda: eng.tree(ctx), 300)
        print(f"{'build command tree (song)':44s} {m:10.3f} {w:10.3f}")

        def gesture():
            s = eng.new_session(ctx)
            t = drag(s, (500, 400), [(-90, 0), (0, 90), (90, 0)], step=2)
            eng.finish(s, s.release(t + 5))
        m, w = timed(gesture, 100)
        print(f"{'LEFT-DOWN-RIGHT: ~135 moves + commit':44s} {m:10.3f} {w:10.3f}")

        s = eng.new_session(ctx)
        s.press(0, 0, 0)
        t0 = time.perf_counter()
        n = 20000
        for i in range(n):
            s.move(-(i % 400), 0, i)
        per = (time.perf_counter() - t0) / n * 1e6
        print(f"{'pointer move handling (per event)':44s} {per:8.1f} us")
        print("frame budget at 60 Hz: 16.7 ms")


if __name__ == "__main__":
    main()
