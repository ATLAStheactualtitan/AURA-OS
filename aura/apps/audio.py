"""Audio playback and output-device enumeration (Qt Multimedia; PipeWire/Pulse verification when tools exist)."""
import json
import os
import shutil
import subprocess

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer


def _id(dev) -> str:
    return bytes(dev.id()).decode("utf-8", "replace")


def _run(args, timeout=2.0):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


class AudioEngine(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.out = QAudioOutput(self)
        self.player.setAudioOutput(self.out)
        self.player.playbackStateChanged.connect(lambda *_: self.stateChanged.emit())
        self.player.errorOccurred.connect(self._on_error)
        self.current_path = ""
        self.current_device = ""
        self.last_error = ""
        self._media = QMediaDevices(self)

    def _on_error(self, err, text):
        self.last_error = text
        self.stateChanged.emit()

    def devices(self) -> list:
        default = QMediaDevices.defaultAudioOutput()
        return [dict(id=_id(d), name=d.description(), default=(_id(d) == _id(default))) for d in QMediaDevices.audioOutputs()]

    def play(self, path, device_id=None, device_name="") -> tuple:
        """Returns (ok, message). Never claims routing that was not requested of the audio server."""
        if not os.path.exists(path):
            return False, f"File missing: {os.path.basename(path)}"
        target = None
        if device_id:
            target = next((d for d in QMediaDevices.audioOutputs() if _id(d) == device_id), None)
            if target is None:
                return False, f"Output unavailable: {device_name or device_id}. Playback not started."
            self.out.setDevice(target)
        else:
            self.out.setDevice(QMediaDevices.defaultAudioOutput())
        self.last_error = ""
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.current_path = path
        used = self.out.device()
        self.current_device = used.description()
        msg = f"Playing {os.path.basename(path)} on {used.description()}"
        if device_id and _id(used) != device_id:
            return False, f"Qt did not accept output {device_name}; using {used.description()}"
        v = self.verify_sink()
        if v:
            msg += f" (server confirms sink: {v})"
        return True, msg

    def verify_sink(self) -> str:
        """Ask PipeWire/Pulse which sink our stream is attached to. Empty when tools are missing."""
        if not shutil.which("pactl"):
            return ""
        try:
            inputs = json.loads(_run(["pactl", "--format=json", "list", "sink-inputs"]) or "[]")
            sinks = {s["index"]: s.get("description", s.get("name")) for s in json.loads(_run(["pactl", "--format=json", "list", "sinks"]) or "[]")}
            for i in inputs:
                if i.get("properties", {}).get("application.process.id") == str(os.getpid()):
                    return str(sinks.get(i["sink"], i["sink"]))
        except Exception:
            pass
        return ""

    def toggle(self) -> str:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            return "Paused"
        if self.current_path:
            self.player.play()
            return "Resumed"
        return ""

    def stop(self):
        self.player.stop()

    @property
    def playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlayingState

    def pipewire_status(self) -> str:
        if shutil.which("wpctl"):
            return _run(["wpctl", "status"], 3.0) or "wpctl returned nothing"
        return "wpctl (WirePlumber) not found on this system"
