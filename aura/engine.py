"""Engine: wires store, grammar, dispatch, apps and adaptation together (no Qt UI dependency)."""
import os
from dataclasses import fields
from pathlib import Path

from .adaptive import Proficiency
from .apps.actions import EditorState, Services, build_registry, register_handlers
from .apps.files import FileService
from .apps.music import MusicLibrary, make_sample_tones
from .core.context import default_model
from .core.dispatch import Command, Dispatcher, Result
from .core.grammar import DEFAULT_FAMILY_MAP, validate_family_map
from .core.recognizer import RecognizerConfig
from .core.session import GestureSession, Outcome
from .store import Store


def ensure_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if not (root / "Documents").exists():
        (root / "Documents").mkdir()
        (root / "Documents" / "welcome.txt").write_text(
            "Welcome to AURA.\n\nRight-click and drag: LEFT, then DOWN, then RIGHT on a song plays it on your assigned speaker.\n"
            "Try FIND (UP) on this document.\n", encoding="utf-8")
        (root / "Documents" / "todo.txt").write_text("- try the gesture lab\n- assign a speaker\n- rename this file\n", encoding="utf-8")
        (root / "Projects").mkdir()
        (root / "Projects" / "readme.md").write_text("# Project\nSample folder for Files.\n", encoding="utf-8")
        (root / "Archive").mkdir()
    make_sample_tones(root / "Music" / "Sample Tones")
    return root


class Engine:
    def __init__(self, store=None, audio=None, ui=None, workspace=None):
        self.store = store or Store()
        self.workspace = ensure_workspace(Path(workspace or os.environ.get("AURA_WORKSPACE", Path.home() / "AURA_Workspace")))
        self.files = FileService(self.store, [self.workspace])
        music_dirs = [self.workspace / "Music"] + ([Path.home() / "Music"] if (Path.home() / "Music").is_dir() and not workspace else [])
        self.library = MusicLibrary(self.store, music_dirs)
        self.editor = EditorState()
        self.svc = Services(self.store, self.files, self.library, audio, self.editor, ui)
        self.contexts = default_model()
        self.registry = build_registry()
        self.dispatcher = Dispatcher(self.registry, self.svc)
        register_handlers(self.dispatcher)
        self.prof = Proficiency(self.store)

    # --- configuration -----------------------------------------------------
    @property
    def family_map(self) -> dict:
        m = self.store.get("family_map")
        if not m:
            m = dict(DEFAULT_FAMILY_MAP)
            self.store.set("family_map", m)
        return m

    def set_family_map(self, m: dict):
        validate_family_map(m)
        self.store.set("family_map", m)

    def recognizer_config(self) -> RecognizerConfig:
        cfg = RecognizerConfig()
        valid = {f.name for f in fields(cfg)} - {"directions", "first_directions"}
        for k, v in (self.store.get("recognizer", {}) or {}).items():
            if k in valid:
                setattr(cfg, k, float(v))
        g = self.prof.guidance()
        cfg.pause_ms = max(1.0, float(g["menu_delay_ms"])) if g["menu_delay_ms"] else cfg.pause_ms
        return cfg

    # --- gestures -------------------------------------------------------------
    def context(self, type_name, data=None):
        return self.contexts.resolve(type_name, data)

    def tree(self, ctx):
        return self.registry.build_tree(ctx, self.family_map, self.svc)

    def new_session(self, ctx) -> GestureSession:
        return GestureSession(ctx, self.tree(ctx), self.recognizer_config(), self.prof.familiarity)

    def finish(self, session: GestureSession, outcome: Outcome) -> Result:
        """Log telemetry and, only for a committed gesture, execute its command."""
        res = None
        if outcome.kind == "committed":
            res = self.dispatcher.execute(outcome.command)
            logged = outcome.kind if res.status != "confirm" else "committed"
            if res.status in ("unavailable", "error", "invalid"):
                logged = "unavailable" if res.status == "unavailable" else "invalid"
        else:
            logged = outcome.kind
        if outcome.kind != "click":
            self.store.log_interaction(session.ctx.type, ">".join(outcome.path), outcome.command.action_id if outcome.command else "",
                                       logged, outcome.duration_ms, outcome.first_segment_ms, outcome.segments)
        return res or Result(outcome.kind == "click", outcome.message, "ok" if outcome.kind == "click" else outcome.kind)

    def run_menu(self, ctx, node, confirmed=False) -> Result:
        from .core.dispatch import command_from_node
        cmd = command_from_node(ctx, node)
        res = self.dispatcher.execute(cmd, confirmed)
        if res.status != "confirm":
            self.store.log_interaction(ctx.type, ">".join(node.path), node.action_id, "committed" if res.ok else "error", via="menu")
            if res.ok:
                tip = self.prof.suggestion(">".join(node.path), node.label)
                if tip:
                    res.data["tip"] = tip
        return res

    def execute_key(self, key, ctx, params, confirmed=True) -> Result:
        """Second stage of prompt/confirm flows."""
        cmd = Command(key, ctx, params, (), "", key)
        return self.dispatcher.execute(cmd, confirmed)
