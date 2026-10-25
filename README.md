# AURA — Adaptive Universal Response Architecture (prototype)

An experimental desktop shell built on one gesture grammar:

**Context → Action family → Refinement → Destination**, committed by releasing the right mouse button.

Python 3 + PySide6 (Qt Quick/QML) + SQLite. It runs as an ordinary application; it does **not** replace GNOME or the compositor.

## Run

```bash
./setup.sh            # creates .venv, installs PySide6 + pytest (add --system on Ubuntu for apt libraries, uses sudo)
./run.sh              # fullscreen shell (Ctrl+Q quits)
./run.sh --windowed   # development window
./run.sh --test       # test suite (headless, QT_QPA_PLATFORM=offscreen)
.venv/bin/python -m tools.benchmark
```

On first start AURA creates `~/AURA_Workspace` (sample documents and four generated WAV tones) and authorizes only that folder for Files. User data lives in `~/.local/share/aura/aura.db` (`AURA_HOME` overrides it).

## Using it

- Right-click without moving: contextual menu (each entry shows its gesture).
- Right-click, hold, drag: gesture. Change direction to descend the tree. Release to commit. **Esc cancels.** Invalid or incomplete gestures do nothing.
- Pause during a gesture to reveal the available branches (immediately while in full-guidance mode).
- Context comes from what is under the pointer: song, playlist, folder, file, document, app icon, app background, desktop.

### Gesture grammar (stable, configurable in the DB `family_map`)

| First segment | Family | Examples |
|---|---|---|
| ← | ACT | Play song, open folder, new document |
| ↑ | FIND | Search document / folder / app (same concept, scoped by context) |
| → | MODIFY | Rename, edit, uppercase |
| ↓ | ORGANIZE | Queue, sort, move/copy |
| ↖ | PRESERVE | Save, favorite, bookmark |
| ↗ | NAVIGATE | Go to app / parent folder / playlist |
| ↙ | REVERSE | Undo, redo, stop |

Only the first segment may be diagonal; all later segments are cardinal. The recogniser accepts any direction set, so diagonals can be enabled at deeper levels later.

### The mandatory music example

Right-click a song, then: `←` plays on the default output · `← ↓` lists output devices · `← ↓ →` plays on the speaker assigned to slot RIGHT.
Assign devices to LEFT/UP/RIGHT in Music → Outputs. Assignments are stored by device id and never shift when devices appear or disappear. A missing device shows as unavailable and playback is **not** started.

## Architecture

```
aura/core/        directions, recognizer (pure, time injected), context hierarchy, grammar, session, dispatch
aura/apps/        music library, audio engine (Qt Multimedia), file service, action declarations + handlers
aura/store.py     SQLite: settings, slot assignments, favorites, interaction telemetry
aura/adaptive.py  interpretable proficiency model (counters + thresholds)
aura/engine.py    wiring, no UI dependency
aura/ui/          Qt bridge (Controller) and QML shell (overlay, windows, apps)
tests/  tools/   unit + end-to-end tests, benchmark, screenshot helper
```

Actions declare the context types they apply to; the grammar picks the most specific declaration per gesture path, so `FIND` on a document, a folder, or an app background are different handlers behind the same gesture. Conflicting declarations raise an error (tested for every context type).

## Adaptive guidance

Levels 0–3 (Guided, Assisted, Compact, Fluent) from successful-gesture counts and recent success rate. Higher levels delay and shrink the menu. Per-path familiarity (●○○ … ●●●) and recommendation (★) markers are shown next to options that are always in the same fixed position; unavailable options carry ⊘. Menu use of the same action 3+ times triggers a tip with the gesture. Settings → disable adaptation, restore full guidance, reset data.

## What was verified (macOS arm64 dev host, Python 3.14, PySide6 6.12)

- 49 automated tests pass: direction recognition, multi-segment gestures, hysteresis/reversal, pause, cancel, context inheritance, conflict detection, command resolution, stable mappings, incomplete/invalid gestures, destructive confirmation, file operations and authorization, editor Save/Save As, proficiency tracking.
- End-to-end tests deliver real synthetic right-button `QMouseEvent`s to the QML window; the live overlay state, `← ↓ →` on a song, Esc cancel and the click menu are asserted.
- The shell launches under both the `offscreen` and `cocoa` Qt platforms. Real audio devices were enumerated and a WAV was played via Qt Multimedia.
- Benchmark: command-tree build ≈ 0.02 ms, a full 3-segment gesture with commit ≈ 0.2 ms.

## Not verified / limitations (be aware)

- **Not yet run on Ubuntu ARM64 / UTM.** PipeWire sink confirmation (`pactl`), `wpctl status`, and routing to a specific PipeWire sink are implemented but untested here. Routing is requested through Qt Multimedia's PulseAudio/PipeWire-pulse backend (`QAudioOutput.setDevice`). The status message says "server confirms sink" only if `pactl` actually reports it. In UTM you typically get a single virtual sink, so test multi-device behaviour with a USB/virtual sink.
- Input is captured **only inside AURA's own windows**. System-wide Wayland capture is not implemented (Wayland forbids it without compositor cooperation).
- Editor: single document; Undo/Redo/transform use the QML `TextArea` engine. Find is next/prev in the open document.
- Files: delete moves to `AURA_HOME/trash` after confirmation and can be undone from REVERSE in Files. Move/copy destination: the node itself starts a "choose destination" mode; `→` = assigned folder (default: authorized root) and `↓` = authorized root.
- Colour-independent markers exist (glyphs, outlines, dots) but a full accessibility audit has not been done.
- On macOS, venv files can be flagged "hidden", which stops Qt from finding its plugins; `run.sh` clears the flag.
