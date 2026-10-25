"""File operations restricted to user-authorized roots, with an undo stack and a recoverable trash."""
import os
import shutil
import time
from pathlib import Path

from ..store import aura_home


class FileError(Exception):
    pass


class FileService:
    def __init__(self, store, default_roots=None):
        self.store = store
        if store.get("files.roots") is None:
            store.set("files.roots", [str(Path(p)) for p in (default_roots or [])])
        self.undo_stack: list = []

    # --- authorization -----------------------------------------------------
    @property
    def roots(self) -> list:
        return [Path(p) for p in self.store.get("files.roots", [])]

    def authorize(self, path):
        p = str(Path(path).resolve())
        roots = self.store.get("files.roots", [])
        if p not in roots:
            self.store.set("files.roots", roots + [p])

    def revoke(self, path):
        self.store.set("files.roots", [r for r in self.store.get("files.roots", []) if r != str(path)])

    def check(self, path) -> Path:
        p = Path(path).resolve()
        if not any(p == r.resolve() or r.resolve() in p.parents for r in self.roots):
            raise FileError(f"{p} is outside the authorized folders")
        return p

    # --- queries -----------------------------------------------------------
    def listdir(self, path) -> list:
        p = self.check(path)
        out = []
        for e in sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if e.name.startswith("."):
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            out.append(dict(name=e.name, path=str(e), isDir=e.is_dir(), size=st.st_size, mtime=st.st_mtime))
        return out

    def search(self, root, query, limit=200) -> list:
        root = self.check(root)
        q, out = query.lower(), []
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if not d.startswith(".")]
            for n in dn + fn:
                if q in n.lower():
                    fp = Path(dp) / n
                    out.append(dict(name=n, path=str(fp), isDir=fp.is_dir(), size=0, mtime=0))
                    if len(out) >= limit:
                        return out
        return out

    # --- mutations -----------------------------------------------------------
    def rename(self, path, new_name) -> Path:
        src = self.check(path)
        if not new_name or "/" in new_name or new_name in (".", ".."):
            raise FileError("Invalid name")
        dst = src.with_name(new_name)
        if dst.exists():
            raise FileError(f"{new_name} already exists")
        src.rename(self.check(dst))
        self.undo_stack.append(("move", dst, src))
        return dst

    def move(self, path, dest_dir) -> Path:
        src, d = self.check(path), self.check(dest_dir)
        if not d.is_dir():
            raise FileError("Destination is not a folder")
        if d == src or src in d.parents:
            raise FileError("Cannot move a folder into itself")
        dst = d / src.name
        if dst.exists():
            raise FileError(f"{src.name} already exists in {d.name}")
        shutil.move(str(src), str(dst))
        self.undo_stack.append(("move", dst, src))
        return dst

    def copy(self, path, dest_dir) -> Path:
        src, d = self.check(path), self.check(dest_dir)
        if not d.is_dir():
            raise FileError("Destination is not a folder")
        dst = d / src.name
        if dst.exists():
            raise FileError(f"{src.name} already exists in {d.name}")
        if src.is_dir():
            if src in d.parents or d == src:
                raise FileError("Cannot copy a folder into itself")
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        self.undo_stack.append(("remove", dst, None))
        return dst

    def trash(self, path) -> Path:
        src = self.check(path)
        tdir = aura_home() / "trash"
        tdir.mkdir(parents=True, exist_ok=True)
        dst = tdir / f"{int(time.time()*1000)}-{src.name}"
        shutil.move(str(src), str(dst))
        self.undo_stack.append(("move", dst, src))
        return dst

    def mkdir(self, parent, name) -> Path:
        p = self.check(parent) / name
        p.mkdir()
        self.undo_stack.append(("remove", p, None))
        return p

    def undo(self) -> str:
        if not self.undo_stack:
            raise FileError("Nothing to undo")
        kind, a, b = self.undo_stack.pop()
        if kind == "move":
            if b.exists():
                raise FileError(f"{b.name} exists; cannot restore")
            shutil.move(str(a), str(b))
            return f"Restored {b.name}"
        shutil.rmtree(a) if a.is_dir() else a.unlink()
        return f"Removed {a.name}"

    @staticmethod
    def is_text(path) -> bool:
        try:
            with open(path, "rb") as f:
                return b"\0" not in f.read(2048)
        except OSError:
            return False
