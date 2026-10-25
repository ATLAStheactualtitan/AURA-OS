"""Semantic gesture grammar: Context -> Action family -> Refinement -> Destination.

The family->direction mapping is stable and configurable. Actions are declared with the
context types they apply to; the most specific context in the hierarchy wins per path.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from .context import Context

FAMILIES = {
    "ACT": "Execute, play, launch, activate",
    "PRESERVE": "Save, archive, bookmark, retain",
    "FIND": "Search, locate, discover",
    "ORGANIZE": "Move, sort, group, arrange",
    "MODIFY": "Edit, rename, transform, change",
    "NAVIGATE": "Move between locations or views",
    "REVERSE": "Undo, go back, restore",
}

DEFAULT_FAMILY_MAP = {
    "LEFT": "ACT",
    "UP": "FIND",
    "RIGHT": "MODIFY",
    "DOWN": "ORGANIZE",
    "UP_LEFT": "PRESERVE",
    "UP_RIGHT": "NAVIGATE",
    "DOWN_LEFT": "REVERSE",
}


class GrammarError(Exception):
    pass


def validate_family_map(m: dict):
    from .directions import BY_NAME
    for d, f in m.items():
        if d not in BY_NAME:
            raise GrammarError(f"unknown direction {d}")
        if f not in FAMILIES:
            raise GrammarError(f"unknown family {f}")
    if len(set(m.values())) != len(m):
        raise GrammarError("a family may only be mapped to one direction")


@dataclass
class NodeSpec:
    """A dynamically provided child (e.g. an output device slot)."""
    direction: str
    label: str
    action_id: str
    params: dict = field(default_factory=dict)
    available: bool = True
    reason: str = ""


@dataclass
class ActionDef:
    id: str
    family: str
    path: tuple                     # refinement directions after the family direction
    label: str
    contexts: tuple                 # context type names this applies to (inherited by children)
    params: dict = field(default_factory=dict)
    requires: Optional[Callable] = None     # (ctx, svc) -> (ok, reason)
    children: Optional[Callable] = None     # (ctx, svc) -> [NodeSpec]
    recommend: Optional[Callable] = None    # (ctx, svc) -> bool
    handler: str = ""
    destructive: bool = False
    hint: str = ""
    branch_only: bool = False       # chooser node: entering it commits nothing


@dataclass
class Node:
    direction: Optional[str]
    label: str
    family: str = ""
    path: tuple = ()
    action_id: Optional[str] = None
    params: dict = field(default_factory=dict)
    available: bool = True
    reason: str = ""
    destructive: bool = False
    recommended: bool = False
    hint: str = ""
    children: dict = field(default_factory=dict)

    def walk(self):
        yield self
        for c in self.children.values():
            yield from c.walk()


class Registry:
    def __init__(self):
        self.defs: dict = {}

    def register(self, d: ActionDef):
        if d.id in self.defs:
            raise GrammarError(f"duplicate action id {d.id}")
        if d.family not in FAMILIES:
            raise GrammarError(f"unknown family {d.family}")
        self.defs[d.id] = d
        return d

    def applicable(self, ctx: Context):
        """Yield (def, specificity) where specificity 0 is the most specific context."""
        for d in self.defs.values():
            hits = [ctx.chain.index(c) for c in d.contexts if c in ctx.chain]
            if hits:
                yield d, min(hits)

    def build_tree(self, ctx: Context, family_map: dict, svc=None) -> Node:
        by_family = {f: d for d, f in family_map.items()}
        best: dict = {}
        for d, spec in self.applicable(ctx):
            key = (d.family, d.path)
            cur = best.get(key)
            if cur is None or spec < cur[1]:
                best[key] = (d, spec)
            elif spec == cur[1]:
                raise GrammarError(f"conflicting actions {cur[0].id} and {d.id} at {key} in {ctx.type}")
        root = Node(None, ctx.label)
        for fam, dname in by_family.items():
            root.children[dname] = Node(dname, fam.title(), fam, (dname,), available=False,
                                        reason=f"No {fam.title()} action for {ctx.label}", hint=FAMILIES[fam])
        for (fam, path), (d, _) in sorted(best.items(), key=lambda kv: len(kv[0][1])):
            if fam not in by_family:
                continue
            cur = root.children[by_family[fam]]
            for step in path:
                nxt = cur.children.get(step)
                if nxt is None:
                    nxt = Node(step, "…", fam, cur.path + (step,), available=False, reason="Incomplete branch")
                    cur.children[step] = nxt
                cur = nxt
            ok, why = (True, "")
            if d.requires:
                ok, why = d.requires(ctx, svc)
            cur.label, cur.action_id = d.label, (None if d.branch_only else d.id)
            cur.params = dict(d.params)
            cur.available, cur.reason = ok, why
            cur.destructive, cur.hint = d.destructive, d.hint
            if d.recommend:
                cur.recommended = bool(d.recommend(ctx, svc))
            if d.branch_only:
                cur.action_id = None
            if d.children:
                for s in d.children(ctx, svc):
                    if s.direction in cur.children and cur.children[s.direction].action_id:
                        continue
                    cur.children[s.direction] = Node(s.direction, s.label, fam, cur.path + (s.direction,),
                                                     s.action_id, dict(s.params), s.available, s.reason)
        # Branch nodes made only of placeholders become unavailable leaves; families with live children are available.
        for fam_node in root.children.values():
            if fam_node.action_id is None and fam_node.children and any(c.available for c in fam_node.walk() if c is not fam_node):
                fam_node.available, fam_node.reason = True, ""
        return root

    def flatten(self, tree: Node):
        """Every executable node, for the contextual menu."""
        return [n for n in tree.walk() if n.action_id]
