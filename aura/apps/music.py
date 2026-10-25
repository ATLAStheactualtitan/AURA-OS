"""Music library: scanning authorised music folders, playlists, sample-tone generation."""
import math
import struct
import wave
from pathlib import Path

AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".oga", ".m4a", ".opus", ".aac"}


def make_sample_tones(folder: Path):
    """Write short real WAV files so playback works on a fresh install."""
    folder.mkdir(parents=True, exist_ok=True)
    notes = {"A4 440Hz": 440.0, "C5 523Hz": 523.25, "E5 659Hz": 659.25, "G4 392Hz": 392.0}
    for name, f in notes.items():
        p = folder / f"Tone {name}.wav"
        if p.exists():
            continue
        rate, secs = 22050, 4
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            frames = bytearray()
            for i in range(rate * secs):
                t = i / rate
                env = min(1.0, t * 20) * min(1.0, (secs - t) * 5)
                frames += struct.pack("<h", int(9000 * env * (math.sin(2*math.pi*f*t) + 0.3*math.sin(4*math.pi*f*t)) / 1.3))
            w.writeframes(bytes(frames))


class MusicLibrary:
    def __init__(self, store, folders):
        self.store = store
        self.folders = [Path(f) for f in folders]
        self.tracks: list = []
        self.queue: list = []
        self.scan()

    def scan(self):
        out = []
        for root in self.folders:
            if not root.is_dir():
                continue
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() in AUDIO_EXT and not p.name.startswith("."):
                    rel = p.parent.relative_to(root)
                    out.append(dict(path=str(p), title=p.stem, artist=(rel.parts[0] if rel.parts else root.name),
                                    album=p.parent.name, ext=p.suffix.lower()))
        self.tracks = out
        return out

    def playlists(self) -> list:
        albums = sorted({t["album"] for t in self.tracks})
        return [dict(id="all", name="Library"), dict(id="fav", name="Favorites"), dict(id="queue", name="Queue")] + \
               [dict(id="album:" + a, name=a) for a in albums]

    def playlist_tracks(self, pid) -> list:
        fav = self.store.favorites()
        if pid == "all":
            res = list(self.tracks)
        elif pid == "fav":
            res = [t for t in self.tracks if t["path"] in fav]
        elif pid == "queue":
            by = {t["path"]: t for t in self.tracks}
            res = [by[p] for p in self.queue if p in by]
        elif pid.startswith("album:"):
            res = [t for t in self.tracks if t["album"] == pid[6:]]
        else:
            res = []
        return [dict(t, fav=t["path"] in fav) for t in res]

    def track(self, path):
        return next((t for t in self.tracks if t["path"] == path), None)
