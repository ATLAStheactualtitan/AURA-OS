"""QObject bridge between QML and the engine. All gesture timing uses the monotonic clock here."""
import json
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from ..engine import Engine


def now_ms() -> float:
    return time.monotonic() * 1000.0


class Controller(QObject):
    gestureChanged = Signal()
    toast = Signal(str, bool, str)
    uiRequest = Signal(str, "QVariant")
    promptRequested = Signal(str, str, int)
    confirmRequested = Signal(str, int)
    settingsChanged = Signal()
    musicChanged = Signal()
    labChanged = Signal()

    def __init__(self, engine: Engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        engine.svc.ui = lambda name, **kw: self.uiRequest.emit(name, kw)
        self.session = None
        self._ctx = None
        self._menu = []
        self._gesture = {"active": False}
        self._pending = {}
        self._token = 0
        self._last_outcome = {}
        self._history = []
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------ gesture state
    def _state(self) -> dict:
        s = self.session
        if not s:
            return {"active": False}
        g = self.engine.prof.guidance()
        rec = s.rec
        node = rec.peak if rec.cur is not None else rec.start
        menu_visible = s.dragging and (g["menu_delay_ms"] == 0 or s.paused)
        step = max(1, len(s.points) // 400)
        return dict(
            active=True, mode="gesture", dragging=s.dragging, paused=s.paused, menuVisible=menu_visible,
            press=dict(x=rec.start[0], y=rec.start[1]), node=dict(x=node[0], y=node[1]), pos=dict(x=rec.pos[0], y=rec.pos[1]),
            points=[dict(x=p[0], y=p[1]) for p in s.points[::step]],
            options=s.options() if s.dragging else [], path=list(s.path), ready=s.ready,
            invalid=s.invalid_dir or "", command=s.command_text, nodeLabel=s.node.label,
            hint=s.node.hint, nodeReason=("" if s.node.available else s.node.reason),
            ctxType=s.ctx.type, ctxLabel=s.ctx.label, detail=g["detail"], level=g["level"],
            leaf=bool(s.path) and not s.node.children, destructive=s.node.destructive,
            log=[f"{t:7.0f} ms  {k:8s} {x}" for t, k, x in s.log][-40:],
            segments=[dict(dir=sg.direction.name, t=sg.t) for sg in rec.segments],
        )

    def _publish(self):
        self._gesture = self._state()
        self.gestureChanged.emit()

    @Property("QVariant", notify=gestureChanged)
    def gesture(self):
        return self._gesture

    @Slot(str, "QVariant", float, float)
    def beginGesture(self, type_name, data, x, y):
        self._ctx = self.engine.context(type_name, dict(data or {}))
        self.session = self.engine.new_session(self._ctx)
        self.session.press(x, y, now_ms())
        self._timer.start()
        self._publish()

    @Slot(float, float)
    def moveGesture(self, x, y):
        if self.session:
            self.session.move(x, y, now_ms())
            self._publish()

    def _tick(self):
        if self.session:
            before = self.session.paused
            self.session.tick(now_ms())
            if self.session.paused != before:
                self._publish()

    @Slot(float, float)
    def endGesture(self, x, y):
        s = self.session
        if not s or s.finished:
            return
        self._timer.stop()
        s.move(x, y, now_ms())
        o = s.release(now_ms())
        if o.kind == "click":
            self._open_menu(s)
            return
        self._complete(s, o)

    @Slot()
    def cancelGesture(self):
        s = self.session
        if s and not s.finished:
            self._timer.stop()
            self._complete(s, s.cancel(now_ms()))
        elif self._menu:
            self.closeMenu()

    @Slot(result=bool)
    def gestureInProgress(self):
        return bool(self.session and not self.session.finished) or bool(self._menu)

    def _complete(self, s, o):
        res = self.engine.finish(s, o)
        self._last_outcome = dict(kind=o.kind, path=" → ".join(o.path), duration=round(o.duration_ms), first=round(o.first_segment_ms),
                                  segments=o.segments, message=res.message or o.message, ctx=s.ctx.label,
                                  command=o.command.action_id if o.command else "", ok=res.ok)
        self._history = ([dict(self._last_outcome, log=[f"{t:7.0f}  {k:8s} {x}" for t, k, x in s.log])] + self._history)[:30]
        self.session = None
        self._gesture = {"active": False}
        self.gestureChanged.emit()
        self.labChanged.emit()
        self.settingsChanged.emit()
        cmd = o.command
        if res.status == "confirm":
            self._confirm_for(cmd)
        else:
            self._report(res, o)

    def _report(self, res, o=None):
        if res.status == "prompt":
            self._token += 1
            self._pending[self._token] = res.data
            self.promptRequested.emit(res.data["title"], res.data["value"], self._token)
            return
        kind = res.status if not res.ok else "ok"
        if o is not None and o.kind not in ("committed", "click"):
            kind = "warn"
        self.toast.emit(res.message, bool(res.ok), kind)
        tip = res.data.get("tip") if res.data else None
        if tip:
            self.toast.emit(tip, True, "tip")

    def _confirm_for(self, cmd):
        self._token += 1
        self._pending[self._token] = dict(cmd=cmd)
        self.confirmRequested.emit(f"{cmd.label}: {cmd.ctx.label}?", self._token)

    @Slot(int, bool)
    def confirmDone(self, token, ok):
        p = self._pending.pop(token, None)
        if not p:
            return
        if not ok:
            self.toast.emit("Cancelled — nothing changed", True, "warn")
            return
        self._report(self.engine.dispatcher.execute(p["cmd"], confirmed=True))

    @Slot(int, str)
    def promptDone(self, token, value):
        p = self._pending.pop(token, None)
        if not p or not value.strip():
            return
        self._report(self.engine.execute_key(p["then"], self._ctx or self.engine.context("desktop"), dict(p["params"], value=value.strip())))

    # ------------------------------------------------------------------ context menu (plain right-click)
    def _open_menu(self, s):
        self._menu = [n for n in self.engine.registry.flatten(s.tree)]
        from ..core.directions import arrows
        items = [dict(index=i, label=n.label, family=n.family.title(), gesture=arrows(n.path), pathKey=">".join(n.path),
                      available=n.available, reason=n.reason, destructive=n.destructive,
                      familiarity=self.engine.prof.familiarity(">".join(n.path)), recommended=n.recommended)
                 for i, n in enumerate(self._menu)]
        self._gesture = dict(active=True, mode="menu", press=dict(x=s.rec.start[0], y=s.rec.start[1]), items=items, ctxLabel=s.ctx.label,
                             ctxType=s.ctx.type)
        self._menu_ctx = s.ctx
        self.session = None
        self.gestureChanged.emit()

    @Slot(int)
    def menuPick(self, i):
        node, ctx = self._menu[i], self._menu_ctx
        self.closeMenu()
        if not node.available:
            self.toast.emit(node.reason or "Unavailable", False, "warn")
            return
        self._ctx = ctx
        res = self.engine.run_menu(ctx, node)
        if res.status == "confirm":
            from ..core.dispatch import command_from_node
            self._confirm_for(command_from_node(ctx, node))
        else:
            self._report(res)
        self.settingsChanged.emit()

    @Slot()
    def closeMenu(self):
        self._menu = []
        self._gesture = {"active": False}
        self.gestureChanged.emit()

    # ------------------------------------------------------------------ direct invocation (toolbar buttons)
    @Slot(str, str, "QVariant")
    def invoke(self, action_id, ctx_type, data):
        d = self.engine.registry.defs[action_id]
        ctx = self.engine.context(ctx_type, dict(data or {}))
        from ..core.dispatch import Command
        self._ctx = ctx
        self._report(self.engine.dispatcher.execute(Command(action_id, ctx, dict(d.params), (), d.family, d.label)))

    # ------------------------------------------------------------------ music
    @Slot(result="QVariant")
    def playlists(self):
        return self.engine.library.playlists()

    @Slot(str, str, result="QVariant")
    def tracks(self, pid, text):
        t = self.engine.library.playlist_tracks(pid)
        if text:
            q = text.lower()
            t = [x for x in t if q in x["title"].lower() or q in x["artist"].lower()]
        return t

    @Slot(result="QVariant")
    def audioDevices(self):
        a = self.engine.svc.audio
        return a.devices() if a else []

    @Slot(result="QVariant")
    def outputAssignments(self):
        return self.engine.store.assignments("music.output")

    @Slot(str, str, str)
    def assignOutput(self, slot, device_id, name):
        self.engine.store.assign("music.output", slot, device_id, name)
        self.musicChanged.emit()
        self.toast.emit(f"{slot} → {name}. Gesture mappings elsewhere are unchanged.", True, "ok")

    @Slot(str)
    def unassignOutput(self, slot):
        self.engine.store.unassign("music.output", slot)
        self.musicChanged.emit()

    @Slot(result=bool)
    def isPlaying(self):
        a = self.engine.svc.audio
        return bool(a and a.playing)

    @Slot(result=str)
    def nowPlaying(self):
        a = self.engine.svc.audio
        t = a and self.engine.library.track(getattr(a, "current_path", ""))
        return f"{t['title']} — {a.current_device}" if t else ""

    @Slot(str)
    def playPlain(self, path):
        ok, msg = self.engine.svc.audio.play(path)
        self.toast.emit(msg, ok, "ok" if ok else "error")

    # ------------------------------------------------------------------ files / editor
    @Slot(result="QVariant")
    def roots(self):
        return [str(r) for r in self.engine.files.roots]

    @Slot(str)
    def addRoot(self, path):
        self.engine.files.authorize(path.replace("file://", ""))
        self.toast.emit("Authorized " + path, True, "ok")

    @Slot(str, result="QVariant")
    def listDir(self, path):
        try:
            return self.engine.files.listdir(path)
        except Exception as e:
            self.toast.emit(str(e), False, "error")
            return []

    @Slot(str, str, result="QVariant")
    def searchFiles(self, path, q):
        try:
            return self.engine.files.search(path, q) if q else self.engine.files.listdir(path)
        except Exception as e:
            self.toast.emit(str(e), False, "error")
            return []

    @Slot(result="QVariant")
    def bookmarks(self):
        return self.engine.store.get("files.bookmarks", [])

    @Slot(str, str)
    def completeTransfer(self, mode, dest):
        t = self.engine.svc.state.get("transfer")
        if not t:
            return
        try:
            fn = self.engine.files.move if mode == "move" else self.engine.files.copy
            fn(t["path"], dest)
            self.toast.emit(f"{mode.title()}d to {dest}", True, "ok")
        except Exception as e:
            self.toast.emit(str(e), False, "error")
        self.engine.svc.state["transfer"] = None
        self.uiRequest.emit("files_refresh", {})

    @Slot(str, result=str)
    def readText(self, path):
        try:
            self.engine.files.check(path)
            return open(path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            self.toast.emit(str(e), False, "error")
            return ""

    @Slot(str, str)
    def editorState(self, path, text):
        self.engine.editor.path, self.engine.editor.text = path, text

    # ------------------------------------------------------------------ settings / proficiency / lab
    @Slot(result="QVariant")
    def settings(self):
        p = self.engine.prof
        return dict(adaptation=p.enabled, guidance=p.guidance(), stats=p.stats(), familyMap=self.engine.family_map,
                    recognizer={k: getattr(self.engine.recognizer_config(), k) for k in ("drag_px", "segment_px", "turn_px", "hysteresis_deg", "pause_ms")})

    @Property("QVariant", notify=settingsChanged)
    def guidanceInfo(self):
        return self.engine.prof.guidance()

    @Slot(bool)
    def setAdaptation(self, on):
        self.engine.store.set("adaptation_enabled", on)
        self.settingsChanged.emit()

    @Slot()
    def resetProficiency(self):
        self.engine.prof.reset()
        self.settingsChanged.emit()
        self.toast.emit("Proficiency data cleared", True, "ok")

    @Slot()
    def restoreGuidance(self):
        self.engine.prof.restore_full_guidance()
        self.settingsChanged.emit()
        self.toast.emit("Full guidance restored", True, "ok")

    @Slot(str, float)
    def setThreshold(self, key, value):
        r = dict(self.engine.store.get("recognizer", {}) or {})
        r[key] = value
        self.engine.store.set("recognizer", r)
        self.settingsChanged.emit()

    @Property("QVariant", notify=labChanged)
    def lastOutcome(self):
        return self._last_outcome

    @Property("QVariant", notify=labChanged)
    def history(self):
        return self._history

    @Slot(str, "QVariant", result="QVariant")
    def treeFor(self, type_name, data):
        """Flattened command tree, for the lab inspector."""
        ctx = self.engine.context(type_name, dict(data or {}))
        out = []

        def walk(n, depth):
            for d, c in n.children.items():
                out.append(dict(depth=depth, dir=d, label=c.label, family=c.family, available=c.available, reason=c.reason,
                                action=c.action_id or ""))
                walk(c, depth + 1)
        walk(self.engine.tree(ctx), 0)
        return out

    @Slot(result=str)
    def pipewire(self):
        a = self.engine.svc.audio
        return a.pipewire_status() if a else "No audio engine"
