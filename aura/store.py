"""Local SQLite persistence: settings, stable slot assignments, interaction telemetry."""
import json
import os
import sqlite3
import time
from pathlib import Path


def aura_home() -> Path:
    p = Path(os.environ.get("AURA_HOME", Path.home() / ".local" / "share" / "aura"))
    p.mkdir(parents=True, exist_ok=True)
    return p


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assignments(
  scope TEXT NOT NULL, slot TEXT NOT NULL, target TEXT NOT NULL, label TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(scope, slot));
CREATE TABLE IF NOT EXISTS interactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, ctx TEXT, path TEXT, action TEXT,
  outcome TEXT NOT NULL, duration_ms REAL, first_ms REAL, segments INTEGER, via TEXT NOT NULL DEFAULT 'gesture');
CREATE TABLE IF NOT EXISTS favorites(path TEXT PRIMARY KEY);
"""


class Store:
    def __init__(self, path=None):
        path = ":memory:" if path == ":memory:" else str(path or aura_home() / "aura.db")
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    # settings
    def get(self, key, default=None):
        r = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(r[0]) if r else default

    def set(self, key, value):
        self.db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)))
        self.db.commit()

    # slot assignments (stable: a slot only changes when the user changes it)
    def assign(self, scope, slot, target, label=""):
        self.db.execute("INSERT INTO assignments VALUES(?,?,?,?) ON CONFLICT(scope,slot) DO UPDATE SET target=excluded.target,label=excluded.label",
                        (scope, slot, target, label))
        self.db.commit()

    def unassign(self, scope, slot):
        self.db.execute("DELETE FROM assignments WHERE scope=? AND slot=?", (scope, slot))
        self.db.commit()

    def assignment(self, scope, slot):
        r = self.db.execute("SELECT target,label FROM assignments WHERE scope=? AND slot=?", (scope, slot)).fetchone()
        return {"target": r[0], "label": r[1]} if r else None

    def assignments(self, scope) -> dict:
        return {s: {"target": t, "label": l} for s, t, l in
                self.db.execute("SELECT slot,target,label FROM assignments WHERE scope=?", (scope,))}

    # favorites
    def toggle_favorite(self, path) -> bool:
        if self.db.execute("SELECT 1 FROM favorites WHERE path=?", (path,)).fetchone():
            self.db.execute("DELETE FROM favorites WHERE path=?", (path,))
            on = False
        else:
            self.db.execute("INSERT INTO favorites VALUES(?)", (path,))
            on = True
        self.db.commit()
        return on

    def favorites(self) -> set:
        return {r[0] for r in self.db.execute("SELECT path FROM favorites")}

    # telemetry
    def log_interaction(self, ctx, path, action, outcome, duration_ms=0.0, first_ms=0.0, segments=0, via="gesture", ts=None):
        self.db.execute("INSERT INTO interactions(ts,ctx,path,action,outcome,duration_ms,first_ms,segments,via) VALUES(?,?,?,?,?,?,?,?,?)",
                        (ts or time.time(), ctx, path, action, outcome, duration_ms, first_ms, segments, via))
        self.db.commit()

    def interactions(self, since=0.0, limit=None):
        q = "SELECT ts,ctx,path,action,outcome,duration_ms,first_ms,segments,via FROM interactions WHERE ts>=? ORDER BY id DESC"
        if limit:
            q += f" LIMIT {int(limit)}"
        keys = "ts ctx path action outcome duration_ms first_ms segments via".split()
        return [dict(zip(keys, r)) for r in self.db.execute(q, (since,))]

    def reset_interactions(self):
        self.db.execute("DELETE FROM interactions")
        self.db.commit()
