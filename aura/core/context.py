"""Hierarchical context model: object -> container -> application background -> desktop."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextType:
    name: str
    kind: str            # background | container | object
    parent: str
    label: str


@dataclass
class Context:
    type: str
    kind: str
    label: str
    data: dict = field(default_factory=dict)
    chain: tuple = ()    # type names from this context up to the root


class ContextModel:
    def __init__(self):
        self.types: dict = {}

    def define(self, name, kind, parent, label):
        self.types[name] = ContextType(name, kind, parent, label)

    def chain(self, name):
        out, seen = [], set()
        while name and name in self.types and name not in seen:
            seen.add(name)
            out.append(name)
            name = self.types[name].parent
        return tuple(out)

    def resolve(self, type_name, data=None) -> Context:
        if type_name not in self.types:
            type_name = "desktop"
        t = self.types[type_name]
        data = dict(data or {})
        return Context(t.name, t.kind, str(data.get("title") or data.get("name") or t.label), data, self.chain(type_name))


def default_model() -> ContextModel:
    m = ContextModel()
    d = m.define
    d("desktop", "background", "", "Desktop")
    d("app_icon", "object", "desktop", "Application")
    d("app:music", "background", "desktop", "Music")
    d("playlist", "container", "app:music", "Playlist")
    d("song", "object", "playlist", "Song")
    d("app:files", "background", "desktop", "Files")
    d("files_pane", "container", "app:files", "Folder")
    d("folder_item", "object", "files_pane", "Folder")
    d("file_item", "object", "files_pane", "File")
    d("app:editor", "background", "desktop", "Editor")
    d("document", "object", "app:editor", "Document")
    d("app:lab", "background", "desktop", "Gesture Lab")
    d("lab_panel", "container", "app:lab", "Lab panel")
    d("lab_object", "object", "lab_panel", "Lab object")
    d("app:settings", "background", "desktop", "Settings")
    return m
