import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtMultimedia")


def test_audio_enumeration_and_missing_device(tmp_path):
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication([])
    from aura.apps.audio import AudioEngine
    from aura.apps.music import make_sample_tones
    eng = AudioEngine()
    devs = eng.devices()
    assert isinstance(devs, list)
    make_sample_tones(tmp_path)
    wav = str(next(tmp_path.glob("*.wav")))
    ok, msg = eng.play(wav, "definitely-not-a-device", "Ghost Speaker")
    assert not ok and "unavailable" in msg.lower()
    assert eng.current_path == ""                      # nothing started
    ok, msg = eng.play(str(tmp_path / "missing.wav"))
    assert not ok


def test_sample_tones_are_real_wavs(tmp_path):
    import wave
    from aura.apps.music import make_sample_tones
    make_sample_tones(tmp_path)
    files = list(tmp_path.glob("*.wav"))
    assert len(files) == 4
    with wave.open(str(files[0])) as w:
        assert w.getnframes() > 22050 and w.getframerate() == 22050
