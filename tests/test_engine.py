import pytest

from aura.core.grammar import GrammarError

from conftest import drag

SONG = dict(path="/x/Tone A4 440Hz.wav", title="Tone A4 440Hz", artist="AURA")


@pytest.fixture
def song_ctx(engine):
    t = engine.library.tracks[0]
    return engine.context("song", dict(path=t["path"], title=t["title"], artist=t["artist"]))


def gesture(engine, ctx, legs, start=(500, 400)):
    s = engine.new_session(ctx)
    t = drag(s, start, legs)
    return s, s.release(t + 10)


def test_context_inheritance_chain(engine):
    c = engine.context("song")
    assert c.chain == ("song", "playlist", "app:music", "desktop")


def test_find_is_analogous_across_contexts(engine):
    labels = {}
    for t, d in (("document", {}), ("folder_item", {"path": "/x"}), ("app:music", {})):
        tree = engine.tree(engine.context(t, d))
        labels[t] = tree.children["UP"].label
    assert labels == {"document": "Find in document", "folder_item": "Search this folder", "app:music": "Search music"}


def test_parent_context_actions_inherited(engine):
    tree = engine.tree(engine.context("song"))
    assert tree.children["RIGHT"].label == "Rename track file"       # song overrides desktop settings
    assert tree.children["UP_RIGHT"].label.startswith("Playlists")   # from container
    assert engine.tree(engine.context("app:music")).children["UP_RIGHT"].label == "Go to"  # from desktop


def test_no_conflicts_in_any_context(engine):
    for t in engine.contexts.types:
        engine.tree(engine.context(t))


def test_conflict_detection(engine):
    from aura.core.grammar import ActionDef
    engine.registry.register(ActionDef("dup.a", "ACT", (), "A", ("song",)))
    with pytest.raises(GrammarError):
        engine.tree(engine.context("song"))


def test_left_plays_on_default(engine, song_ctx):
    s, o = gesture(engine, song_ctx, [(-80, 0)])
    assert o.kind == "committed" and o.command.action_id == "music.play"
    r = engine.finish(s, o)
    assert r.ok and engine.svc.audio.played == [("Tone A4 440Hz.wav", None)]


def test_left_down_lists_outputs(engine, song_ctx, ui_calls):
    s, o = gesture(engine, song_ctx, [(-80, 0), (0, 80)])
    r = engine.finish(s, o)
    assert o.path == ("LEFT", "DOWN") and "Desk Speaker" in r.message
    assert ("show_outputs" in [c[0] for c in ui_calls])
    assert engine.svc.audio.played == []


def test_left_down_right_plays_on_assigned_speaker(engine, song_ctx):
    engine.store.assign("music.output", "RIGHT", "spk1", "Desk Speaker")
    s, o = gesture(engine, song_ctx, [(-80, 0), (0, 80), (80, 0)])
    assert o.path == ("LEFT", "DOWN", "RIGHT")
    r = engine.finish(s, o)
    assert r.ok and engine.svc.audio.played[-1][1] == "spk1"


def test_missing_device_is_unavailable_and_not_played(engine, song_ctx):
    engine.store.assign("music.output", "RIGHT", "gone", "Old Speaker")
    s, o = gesture(engine, song_ctx, [(-80, 0), (0, 80), (80, 0)])
    assert o.kind == "unavailable" and "not connected" in o.message
    engine.finish(s, o)
    assert engine.svc.audio.played == []


def test_unassigned_slot_does_not_play(engine, song_ctx):
    s, o = gesture(engine, song_ctx, [(-80, 0), (0, 80), (80, 0)])
    r = engine.finish(s, o)
    assert not r.ok and engine.svc.audio.played == []


def test_assignments_are_stable_when_devices_change(engine, song_ctx):
    engine.store.assign("music.output", "RIGHT", "spk1", "Desk Speaker")
    engine.svc.audio.devs.insert(0, dict(id="new", name="New Speaker", default=False))
    tree = engine.tree(song_ctx)
    n = tree.children["LEFT"].children["DOWN"].children["RIGHT"]
    assert n.params["slot"] == "RIGHT" and n.label == "Desk Speaker" and n.available


def test_family_mapping_persists_and_is_validated(engine):
    m = dict(engine.family_map)
    assert engine.family_map == m and m["LEFT"] == "ACT"
    swapped = dict(m, LEFT="FIND", UP="ACT")
    engine.set_family_map(swapped)
    assert engine.tree(engine.context("song")).children["UP"].family == "ACT"
    with pytest.raises(GrammarError):
        engine.set_family_map(dict(m, UP="ACT"))


def test_incomplete_gesture_does_nothing(engine, song_ctx):
    s, o = gesture(engine, song_ctx, [(-20, 0)])
    assert o.kind == "incomplete"
    engine.finish(s, o)
    assert engine.svc.audio.played == []


def test_branch_only_node_is_incomplete(engine):
    ctx = engine.context("playlist", dict(id="all", name="Library"))
    s, o = gesture(engine, ctx, [(0, 80)])          # ORGANIZE alone is a branch
    assert o.kind == "incomplete" and o.command is None


def test_invalid_direction_is_nondestructive(engine, song_ctx):
    s, o = gesture(engine, song_ctx, [(-80, 0), (0, -80)])   # LEFT then UP: no such refinement
    assert o.kind == "invalid"
    engine.finish(s, o)
    assert engine.svc.audio.played == []


def test_cancel_mid_gesture(engine, song_ctx):
    s = engine.new_session(song_ctx)
    drag(s, (500, 400), [(-80, 0)])
    o = s.cancel(2000)
    assert o.kind == "cancelled"
    engine.finish(s, o)
    assert engine.svc.audio.played == [] and engine.store.interactions()[0]["outcome"] == "cancelled"


def test_intermediate_segments_have_no_side_effects(engine, song_ctx):
    s = engine.new_session(song_ctx)
    drag(s, (500, 400), [(-80, 0), (0, 80)])
    assert s.ready and engine.svc.audio.played == []      # nothing runs until release


def test_unavailable_families_are_shown(engine):
    tree = engine.tree(engine.context("song"))
    n = tree.children["UP_LEFT"]
    assert n.available                                  # PRESERVE exists for songs
    tree = engine.tree(engine.context("app:music"))
    assert not tree.children["UP_LEFT"].available and tree.children["UP_LEFT"].reason


def test_destructive_requires_confirmation(engine):
    ws = engine.workspace / "Documents" / "todo.txt"
    ctx = engine.context("file_item", dict(path=str(ws), name="todo.txt", dir=str(ws.parent)))
    s, o = gesture(engine, ctx, [(80, 0), (0, 80)])   # MODIFY -> DOWN delete
    assert o.command.action_id == "files.delete"
    r = engine.finish(s, o)
    assert r.status == "confirm" and ws.exists()
    r = engine.dispatcher.execute(o.command, confirmed=True)
    assert r.ok and not ws.exists()
    assert engine.files.undo() and ws.exists()


def test_rename_move_copy_and_authorization(engine):
    from aura.apps.files import FileError
    d = engine.workspace / "Documents"
    new = engine.files.rename(d / "todo.txt", "tasks.txt")
    assert new.exists()
    moved = engine.files.move(new, engine.workspace / "Archive")
    copied = engine.files.copy(moved, d)
    assert copied.exists() and moved.exists()
    with pytest.raises(FileError):
        engine.files.move(copied, engine.workspace / "Archive")    # collision
    with pytest.raises(FileError):
        engine.files.check("/etc/passwd")
    assert [e["name"] for e in engine.files.search(engine.workspace, "tasks")] == ["tasks.txt", "tasks.txt"]


def test_editor_save_and_save_as(engine, tmp_path):
    ctx = engine.context("document", {"title": "Untitled"})
    engine.editor.text = "hello"
    s, o = gesture(engine, ctx, [(-60, -60)])          # PRESERVE (UP_LEFT) -> Save with no path -> prompt
    r = engine.finish(s, o)
    assert r.status == "prompt"
    r = engine.execute_key("editor.save_as_apply", ctx, {"value": "note.txt"})
    assert r.ok and (engine.workspace / "note.txt").read_text() == "hello"
    r = engine.execute_key("editor.save_as_apply", ctx, {"value": "/tmp/outside.txt"})
    assert not r.ok
