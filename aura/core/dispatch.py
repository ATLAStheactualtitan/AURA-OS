"""Command validation and dispatch."""
from dataclasses import dataclass, field

from .context import Context
from .grammar import Node, Registry


@dataclass
class Command:
    action_id: str
    ctx: Context
    params: dict
    path: tuple
    family: str
    label: str
    destructive: bool = False

    @property
    def text(self) -> str:
        return f"{self.family} · {self.label} · {self.ctx.label}"


@dataclass
class Result:
    ok: bool
    message: str
    status: str = "ok"     # ok | unavailable | error | confirm | invalid
    data: dict = field(default_factory=dict)


def command_from_node(ctx: Context, node: Node) -> Command:
    return Command(node.action_id, ctx, dict(node.params), node.path, node.family, node.label, node.destructive)


class Dispatcher:
    def __init__(self, registry: Registry, svc=None):
        self.registry = registry
        self.svc = svc
        self.handlers: dict = {}
        self.history: list = []

    def register_handler(self, key: str, fn):
        self.handlers[key] = fn

    def validate(self, cmd: Command) -> Result:
        d = self.registry.defs.get(cmd.action_id)
        if d is None and cmd.action_id not in self.handlers:
            return Result(False, f"Unknown action {cmd.action_id}", "invalid")
        if d is not None:
            if not any(c in cmd.ctx.chain for c in d.contexts):
                return Result(False, f"{d.label} does not apply to {cmd.ctx.label}", "invalid")
            if d.requires:
                ok, why = d.requires(cmd.ctx, self.svc)
                if not ok:
                    return Result(False, why or "Unavailable", "unavailable")
        return Result(True, "valid")

    def execute(self, cmd: Command, confirmed: bool = False) -> Result:
        v = self.validate(cmd)
        if not v.ok:
            return v
        if cmd.destructive and not confirmed:
            return Result(False, f"Confirm: {cmd.label} — {cmd.ctx.label}", "confirm")
        d = self.registry.defs.get(cmd.action_id)
        key = (d.handler or d.id) if d else cmd.action_id
        fn = self.handlers.get(key)
        if fn is None:
            return Result(False, f"No handler for {key}", "error")
        try:
            r = fn(cmd, self.svc)
        except Exception as e:  # handler failures must never crash the shell
            r = Result(False, f"{cmd.label} failed: {e}", "error")
        self.history.append((cmd, r))
        return r
