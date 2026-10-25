"""Action declarations (capabilities per context type) and their handlers.

The engine never checks application names: an action simply declares the context types it applies to.
"""
from pathlib import Path

from ..core.dispatch import Result
from ..core.grammar import ActionDef, NodeSpec, Registry

SLOT_ORDER = ("LEFT", "UP", "RIGHT", "DOWN")
OUT_SCOPE = "music.output"
DEST_SCOPE = "files.dest"


class Services:
    """Everything handlers may touch; injected so tests can fake audio/UI."""
    def __init__(self, store, files, library, audio, editor, ui=None):
        self.store, self.files, self.library, self.audio, self.editor = store, files, library, audio, editor
        self.ui = ui or (lambda name, **kw: None)
        self.state = {"files_dir": "", "playlist": "all", "transfer": None}


class EditorState:
    def __init__(self):
        self.path = ""
        self.text = ""


def _prompt(title, value, then, **params):
    return Result(True, title, "prompt", dict(title=title, value=value, then=then, params=params))


def _files_available(ctx, svc):
    return (True, "") if svc and svc.files.roots else (False, "No authorized folders")


def _has_selection_dir(ctx, svc):
    return (True, "") if ctx.data.get("path") else (False, "Nothing selected")


def build_registry() -> Registry:
    r = Registry()
    add = r.register

    # ---------------- desktop (inherited by every application) ----------------
    add(ActionDef("desktop.show", "ACT", (), "Show desktop", ("desktop",), handler="desktop.show"))
    add(ActionDef("app.launch", "ACT", (), "Launch application", ("app_icon",), handler="desktop.launch"))
    add(ActionDef("desktop.find", "FIND", (), "Search applications", ("desktop",), handler="desktop.launcher"))
    add(ActionDef("desktop.settings", "MODIFY", (), "Settings", ("desktop",), params={"app": "settings"}, handler="desktop.open_app"))
    add(ActionDef("desktop.nav", "NAVIGATE", (), "Go to", ("desktop",), branch_only=True))
    for d, app, label in (("LEFT", "music", "Music"), ("UP", "files", "Files"), ("RIGHT", "editor", "Editor"), ("DOWN", "lab", "Gesture Lab")):
        add(ActionDef(f"desktop.go.{app}", "NAVIGATE", (d,), f"Go to {label}", ("desktop",), params={"app": app}, handler="desktop.open_app"))

    # ---------------- music ----------------
    def outputs(ctx, svc):
        present = {d["id"] for d in svc.audio.devices()}
        out = []
        for slot in ("LEFT", "UP", "RIGHT"):
            a = svc.store.assignment(OUT_SCOPE, slot)
            if not a:
                out.append(NodeSpec(slot, "Assign speaker…", "music.play_slot", {"slot": slot}))
            elif a["target"] not in present:
                out.append(NodeSpec(slot, a["label"], "music.play_slot", {"slot": slot}, False, "Output not connected"))
            else:
                out.append(NodeSpec(slot, a["label"], "music.play_slot", {"slot": slot}))
        return out

    add(ActionDef("music.play", "ACT", (), "Play", ("song",)))
    add(ActionDef("music.choose_output", "ACT", ("DOWN",), "Choose output", ("song",), children=outputs, handler="music.show_outputs",
                  hint="Release here to list outputs"))
    add(ActionDef("music.more_by", "FIND", (), "More by artist", ("song",)))
    add(ActionDef("music.favorite", "PRESERVE", (), "Toggle favorite", ("song",)))
    add(ActionDef("music.rename", "MODIFY", (), "Rename track file", ("song",)))
    add(ActionDef("music.enqueue", "ORGANIZE", (), "Add to queue", ("song",)))
    add(ActionDef("music.play_list", "ACT", (), "Play playlist", ("playlist",)))
    add(ActionDef("music.search_list", "FIND", (), "Search playlist", ("playlist",), handler="music.search"))
    add(ActionDef("music.sort", "ORGANIZE", (), "Sort", ("playlist",), branch_only=True))
    add(ActionDef("music.sort_title", "ORGANIZE", ("LEFT",), "Sort by title", ("playlist",), params={"key": "title"}, handler="music.sort_do"))
    add(ActionDef("music.sort_artist", "ORGANIZE", ("UP",), "Sort by artist", ("playlist",), params={"key": "artist"}, handler="music.sort_do"))
    add(ActionDef("music.pl_nav", "NAVIGATE", (), "Playlists", ("playlist",), branch_only=True))
    add(ActionDef("music.pl_prev", "NAVIGATE", ("LEFT",), "Previous playlist", ("playlist",), params={"step": -1}, handler="music.pl_step"))
    add(ActionDef("music.pl_next", "NAVIGATE", ("RIGHT",), "Next playlist", ("playlist",), params={"step": 1}, handler="music.pl_step"))
    add(ActionDef("music.toggle", "ACT", (), "Play / pause", ("app:music",)))
    add(ActionDef("music.outputs", "ACT", ("DOWN",), "Output devices", ("app:music",), handler="music.show_outputs"))
    add(ActionDef("music.find_app", "FIND", (), "Search music", ("app:music",), handler="music.search"))
    add(ActionDef("music.stop", "REVERSE", (), "Stop playback", ("app:music",)))

    # ---------------- files ----------------
    def move_dests(ctx, svc):
        return _dest_specs(ctx, svc, "move")

    def copy_dests(ctx, svc):
        return _dest_specs(ctx, svc, "copy")

    obj = ("file_item", "folder_item")
    add(ActionDef("files.open_folder", "ACT", (), "Open folder", ("folder_item",)))
    add(ActionDef("files.open_file", "ACT", (), "Open in editor", ("file_item",)))
    add(ActionDef("files.refresh", "ACT", (), "Refresh", ("files_pane",)))
    add(ActionDef("files.search_folder", "FIND", (), "Search this folder", ("files_pane", "folder_item"), handler="files.search"))
    add(ActionDef("files.search_all", "FIND", (), "Search authorized folders", ("app:files",), handler="files.search"))
    add(ActionDef("files.bookmark", "PRESERVE", (), "Bookmark", ("files_pane",) + obj))
    add(ActionDef("files.rename", "MODIFY", (), "Rename", obj, requires=_has_selection_dir))
    add(ActionDef("files.delete", "MODIFY", ("DOWN",), "Delete (to trash)", obj, destructive=True))
    add(ActionDef("files.mkdir", "MODIFY", (), "New folder", ("files_pane",)))
    add(ActionDef("files.org", "ORGANIZE", (), "Organize", obj, branch_only=True))
    add(ActionDef("files.move_pick", "ORGANIZE", ("LEFT",), "Move to…", obj, children=move_dests, handler="files.transfer_pick", params={"mode": "move"},
                  hint="Release to choose a destination"))
    add(ActionDef("files.copy_pick", "ORGANIZE", ("UP",), "Copy to…", obj, children=copy_dests, handler="files.transfer_pick", params={"mode": "copy"},
                  hint="Release to choose a destination"))
    add(ActionDef("files.nav", "NAVIGATE", (), "Go to", ("files_pane",), branch_only=True))
    add(ActionDef("files.parent", "NAVIGATE", ("LEFT",), "Parent folder", ("files_pane",)))
    add(ActionDef("files.root", "NAVIGATE", ("UP",), "Authorized root", ("files_pane",)))
    add(ActionDef("files.undo", "REVERSE", (), "Undo file operation", ("app:files",)))

    # ---------------- editor ----------------
    add(ActionDef("editor.new", "ACT", (), "New document", ("app:editor",)))
    add(ActionDef("editor.find", "FIND", (), "Find in document", ("document",), handler="editor.cmd", params={"cmd": "find"}))
    add(ActionDef("editor.find_app", "FIND", (), "Find in editor", ("app:editor",), handler="editor.cmd", params={"cmd": "find"}))
    add(ActionDef("editor.save", "PRESERVE", (), "Save", ("document",)))
    add(ActionDef("editor.save_as", "PRESERVE", ("DOWN",), "Save As…", ("document",)))
    add(ActionDef("editor.edit", "MODIFY", (), "Edit", ("document",), handler="editor.cmd", params={"cmd": "focus"}))
    add(ActionDef("editor.upper", "MODIFY", ("UP",), "UPPERCASE selection", ("document",), handler="editor.cmd", params={"cmd": "upper"}))
    add(ActionDef("editor.lower", "MODIFY", ("DOWN",), "lowercase selection", ("document",), handler="editor.cmd", params={"cmd": "lower"}))
    add(ActionDef("editor.undo", "REVERSE", (), "Undo", ("document",), handler="editor.cmd", params={"cmd": "undo"}))
    add(ActionDef("editor.redo", "REVERSE", ("RIGHT",), "Redo", ("document",), handler="editor.cmd", params={"cmd": "redo"}))

    # ---------------- laboratory ----------------
    for fam in ("ACT", "PRESERVE", "FIND", "ORGANIZE", "MODIFY", "NAVIGATE", "REVERSE"):
        add(ActionDef(f"lab.{fam.lower()}", fam, (), f"Lab {fam.title()}", ("app:lab", "lab_object"), handler="lab.echo"))
    add(ActionDef("lab.act.down", "ACT", ("DOWN",), "Lab: choose", ("lab_object",), handler="lab.echo"))
    add(ActionDef("lab.act.down.right", "ACT", ("DOWN", "RIGHT"), "Lab: third level", ("lab_object",), handler="lab.echo"))
    add(ActionDef("lab.act.down.left", "ACT", ("DOWN", "LEFT"), "Lab: third level (other)", ("lab_object",), handler="lab.echo"))
    return r


def _pane_dir(c) -> str:
    d = c.ctx.data
    return d.get("path", "") if c.ctx.type == "files_pane" else d.get("dir", "")


def _dest_specs(ctx, svc, mode):
    """Destination level: RIGHT = user-assigned folder, DOWN = the first authorized root (both stable)."""
    root = str(svc.files.roots[0]) if svc.files.roots else ""
    a = svc.store.assignment(DEST_SCOPE, "RIGHT")
    assigned = a["target"] if a else root
    out = []
    for slot, label, target in (("RIGHT", "Assigned folder", assigned), ("DOWN", "Authorized root", root)):
        ok = bool(target) and Path(target).is_dir()
        name = Path(target).name or target if target else ""
        out.append(NodeSpec(slot, f"{label}: {name}" if name else label, "files.transfer_to",
                            {"mode": mode, "dest": target}, ok, "" if ok else "Destination unavailable"))
    return out


# ---------------------------------------------------------------- handlers
def register_handlers(disp):
    h = disp.register_handler
    ok = lambda m, **d: Result(True, m, "ok", d)
    bad = lambda m, s="error": Result(False, m, s)

    # desktop
    h("desktop.show", lambda c, s: (s.ui("show_desktop"), ok("Desktop shown"))[1])
    h("desktop.launch", lambda c, s: (s.ui("open_app", app=c.ctx.data.get("app")), ok(f"Launched {c.ctx.label}"))[1])
    h("desktop.launcher", lambda c, s: (s.ui("open_launcher"), ok("Launcher opened"))[1])
    h("desktop.open_app", lambda c, s: (s.ui("open_app", app=c.params["app"]), ok(f"Opened {c.params['app']}"))[1])

    # music
    def track_of(c, s):
        return s.library.track(c.ctx.data.get("path"))

    def play(c, s):
        t = track_of(c, s)
        if not t:
            return bad("Track not found")
        good, msg = s.audio.play(t["path"])
        return Result(good, msg, "ok" if good else "error")
    h("music.play", play)

    def show_outputs(c, s):
        devs = s.audio.devices()
        s.ui("show_outputs", path=c.ctx.data.get("path", ""))
        if not devs:
            return bad("No audio output devices found", "unavailable")
        return ok("Outputs: " + ", ".join(d["name"] + (" (default)" if d["default"] else "") for d in devs))
    h("music.show_outputs", show_outputs)

    def play_slot(c, s):
        slot = c.params["slot"]
        a = s.store.assignment(OUT_SCOPE, slot)
        if not a:
            s.ui("assign_output", slot=slot)
            return bad(f"No speaker assigned to {slot}. Choose one in the Outputs panel.", "unavailable")
        if a["target"] not in {d["id"] for d in s.audio.devices()}:
            return bad(f"Output unavailable: {a['label']}. Playback not started.", "unavailable")
        t = track_of(c, s)
        if not t:
            return bad("Track not found")
        good, msg = s.audio.play(t["path"], a["target"], a["label"])
        return Result(good, msg, "ok" if good else "error")
    h("music.play_slot", play_slot)

    h("music.more_by", lambda c, s: (s.ui("music_filter", text=c.ctx.data.get("artist", "")), ok(f"Showing tracks by {c.ctx.data.get('artist','')}"))[1])
    h("music.search", lambda c, s: (s.ui("music_search"), ok("Search focused"))[1])

    def favorite(c, s):
        on = s.store.toggle_favorite(c.ctx.data["path"])
        s.ui("music_refresh")
        return ok("Added to Favorites" if on else "Removed from Favorites")
    h("music.favorite", favorite)

    def enqueue(c, s):
        s.library.queue.append(c.ctx.data["path"])
        s.ui("music_refresh")
        return ok(f"Queued {c.ctx.label}")
    h("music.enqueue", enqueue)

    h("music.rename", lambda c, s: _prompt("Rename track file", Path(c.ctx.data["path"]).name, "music.rename_apply", path=c.ctx.data["path"]))

    def rename_apply(c, s):
        new = s.files.rename(c.params["path"], c.params["value"])
        s.library.scan()
        s.ui("music_refresh")
        return ok(f"Renamed to {new.name}")
    h("music.rename_apply", rename_apply)

    h("music.play_list", lambda c, s: _play_list(c, s))

    def sort_do(c, s):
        s.ui("music_sort", key=c.params["key"])
        return ok(f"Sorted by {c.params['key']}")
    h("music.sort_do", sort_do)
    h("music.pl_step", lambda c, s: (s.ui("music_playlist_step", step=c.params["step"]), ok("Switched playlist"))[1])

    def toggle(c, s):
        m = s.audio.toggle()
        return ok(m) if m else bad("Nothing to play yet", "unavailable")
    h("music.toggle", toggle)

    def stop(c, s):
        s.audio.stop()
        return ok("Stopped")
    h("music.stop", stop)

    # files
    h("files.open_folder", lambda c, s: (s.ui("files_open", path=c.ctx.data["path"]), ok(f"Opened {c.ctx.label}"))[1])

    def open_file(c, s):
        p = c.ctx.data["path"]
        if not s.files.is_text(p):
            return bad(f"{Path(p).name} is not a text file", "unavailable")
        s.ui("editor_open", path=p)
        return ok(f"Opened {Path(p).name} in Editor")
    h("files.open_file", open_file)

    h("files.refresh", lambda c, s: (s.ui("files_refresh"), ok("Refreshed"))[1])

    def search(c, s):
        base = (c.ctx.data.get("path") if c.ctx.type == "folder_item" else _pane_dir(c)) or (str(s.files.roots[0]) if s.files.roots else "")
        s.ui("files_search", path=base)
        return ok(f"Search in {Path(base).name or base}")
    h("files.search", search)

    def bookmark(c, s):
        p = c.ctx.data["path"]
        b = s.store.get("files.bookmarks", [])
        b = [x for x in b if x != p] if p in b else b + [p]
        s.store.set("files.bookmarks", b)
        s.ui("files_refresh")
        return ok(("Bookmarked " if p in b else "Removed bookmark ") + Path(p).name)
    h("files.bookmark", bookmark)

    h("files.rename", lambda c, s: _prompt("Rename", c.ctx.data["name"], "files.rename_apply", path=c.ctx.data["path"]))

    def rename_apply(c, s):
        new = s.files.rename(c.params["path"], c.params["value"])
        s.ui("files_refresh")
        return ok(f"Renamed to {new.name}")
    h("files.rename_apply", rename_apply)

    def delete(c, s):
        s.files.trash(c.ctx.data["path"])
        s.ui("files_refresh")
        return ok(f"Moved {c.ctx.label} to AURA trash — Undo with REVERSE in Files")
    h("files.delete", delete)

    h("files.mkdir", lambda c, s: _prompt("New folder", "New folder", "files.mkdir_apply", path=_pane_dir(c)))

    def mkdir_apply(c, s):
        p = s.files.mkdir(c.params["path"], c.params["value"])
        s.ui("files_refresh")
        return ok(f"Created {p.name}")
    h("files.mkdir_apply", mkdir_apply)

    def transfer_pick(c, s):
        s.state["transfer"] = dict(mode=c.params["mode"], path=c.ctx.data["path"])
        s.ui("files_transfer", mode=c.params["mode"], path=c.ctx.data["path"])
        return ok(f"{c.params['mode'].title()} {c.ctx.label}: open the destination folder and press “{c.params['mode'].title()} here”")
    h("files.transfer_pick", transfer_pick)

    def transfer_to(c, s):
        dest = c.params["dest"]
        fn = s.files.move if c.params["mode"] == "move" else s.files.copy
        res = fn(c.ctx.data["path"], dest)
        s.ui("files_refresh")
        return ok(f"{c.params['mode'].title()}d {c.ctx.label} to {Path(dest).name}")
    h("files.transfer_to", transfer_to)

    h("files.parent", lambda c, s: (s.ui("files_open", path=str(Path(_pane_dir(c)).parent)), ok("Parent folder"))[1])
    h("files.root", lambda c, s: (s.ui("files_open", path=str(s.files.roots[0])), ok("Authorized root"))[1])
    h("files.undo", lambda c, s: (lambda m: (s.ui("files_refresh"), ok(m))[1])(s.files.undo()))

    # editor
    h("editor.new", lambda c, s: (s.ui("editor_new"), ok("New document"))[1])
    h("editor.cmd", lambda c, s: (s.ui("editor_cmd", cmd=c.params["cmd"]), ok(f"Editor: {c.params['cmd']}"))[1])

    def save(c, s):
        ed = s.editor
        if not ed.path:
            return _prompt("Save As", "untitled.txt", "editor.save_as_apply")
        s.files.check(ed.path)
        Path(ed.path).write_text(ed.text, encoding="utf-8")
        s.ui("editor_saved", path=ed.path)
        return ok(f"Saved {Path(ed.path).name}")
    h("editor.save", save)
    h("editor.save_as", lambda c, s: _prompt("Save As", Path(s.editor.path).name if s.editor.path else "untitled.txt", "editor.save_as_apply"))

    def save_as_apply(c, s):
        v = c.params["value"].strip()
        p = Path(v)
        if not p.is_absolute():
            p = Path(s.store.get("editor.dir") or (s.files.roots[0] if s.files.roots else Path.home())) / v
        s.files.check(p)
        p.write_text(s.editor.text, encoding="utf-8")
        s.editor.path = str(p)
        s.ui("editor_saved", path=str(p))
        return ok(f"Saved as {p.name}")
    h("editor.save_as_apply", save_as_apply)

    # lab
    h("lab.echo", lambda c, s: ok(f"{c.family} / {c.label} on {c.ctx.label} via {' → '.join(c.path)}"))


def _play_list(c, s):
    pid = c.ctx.data.get("id", "all")
    tr = s.library.playlist_tracks(pid)
    if not tr:
        return Result(False, f"{c.ctx.label} is empty", "unavailable")
    s.library.queue = [t["path"] for t in tr[1:]]
    good, msg = s.audio.play(tr[0]["path"])
    return Result(good, msg, "ok" if good else "error")
