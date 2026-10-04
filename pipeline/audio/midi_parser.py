"""MIDI file parser and raw event normalizer.

Converts standard MIDI events and raw onset/frequency event lists
into a unified normalized note schedule:
    [{"note": int, "start": float, "end": float, "velocity": float}]

Note IDs are constrained to MIDI range [21, 108] (A0..C8 piano keys).
All timestamps are in seconds (float). Velocity is 0-127.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import TypedDict

MIN_NOTE = 21   # A0
MAX_NOTE = 108  # C8


class NoteEvent(TypedDict):
    note: int
    start: float
    end: float
    velocity: float


def freq_to_midi(freq: float) -> int:
    """周波数 (Hz) を MIDI ノート番号に変換する。"""
    if freq <= 0:
        return 0
    return int(round(69 + 12 * math.log2(freq / 440.0)))


def parse_raw_events(raw: list[dict]) -> list[NoteEvent]:
    """生のオンセット／周波数／MIDIイベント辞書を正規化 NoteEvent リストに変換する。

    対応キー:
      - 'note': MIDIノート番号 (21..108)
      - 'pitch': 周波数 (Hz)
      - 'start' または 'onset': 開始秒数
      - 'end' または 'duration': 終了秒数
      - 'velocity' または 'amplitude': 音の強さ (0..127)
    """
    events: list[NoteEvent] = []

    for ev in raw:
        # 1. ノート番号の解決
        if "note" in ev:
            note = int(ev["note"])
        elif "pitch" in ev:
            freq = float(ev["pitch"])
            if freq <= 0:
                continue
            note = freq_to_midi(freq)
        else:
            continue

        # 88鍵ピアノ範囲 [21, 108] に収める
        if note < MIN_NOTE or note > MAX_NOTE:
            continue

        # 2. 時間の解決
        start = float(ev.get("start", ev.get("onset", 0.0)))
        if "end" in ev:
            end = float(ev["end"])
        else:
            duration = float(ev.get("duration", 0.2))
            end = start + duration

        if end <= start:
            end = start + 0.05

        # 3. ベロシティの解決
        velocity = float(ev.get("velocity", ev.get("amplitude", 0.8) * 127.0))
        velocity = max(0.0, min(127.0, velocity))

        events.append(NoteEvent(
            note=note,
            start=round(start, 4),
            end=round(end, 4),
            velocity=round(velocity, 2),
        ))

    # 開始時間、ノート番号順でソート
    events.sort(key=lambda e: (e["start"], e["note"]))
    return events


def parse_midi_file(midi_path: str | Path) -> list[NoteEvent]:
    """Parse a Standard MIDI File (.mid) into normalized NoteEvent list.

    Args:
        midi_path: Path to the .mid file.

    Returns:
        List of NoteEvent dicts sorted by start time.
    """
    midi_path = Path(midi_path)
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    try:
        import mido
        return _parse_midi_with_mido(mido, midi_path)
    except ImportError:
        venv_py = Path(r"G:\Dev\piano_transcription_mixed\.venv\Scripts\python.exe")
        if venv_py.exists():
            return _parse_midi_via_subshell(midi_path, venv_py)
        print("[Warning] mido not available in current Python. Cannot parse binary MIDI.", file=sys.stderr)
        return []


def _parse_midi_with_mido(mido_mod, midi_path: Path) -> list[NoteEvent]:
    """Parse MIDI file using mido library with accurate timing."""
    mid = mido_mod.MidiFile(str(midi_path))
    events: list[NoteEvent] = []

    # Active notes: note -> (start_sec, velocity)
    active_notes: dict[int, tuple[float, float]] = {}
    current_time = 0.0

    # mido's iterate iterates in absolute real-time seconds!
    for msg in mid:
        current_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            note = msg.note
            if MIN_NOTE <= note <= MAX_NOTE:
                active_notes[note] = (current_time, float(msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            note = msg.note
            if note in active_notes:
                start_sec, vel = active_notes.pop(note)
                end_sec = current_time
                if end_sec <= start_sec:
                    end_sec = start_sec + 0.05
                events.append(NoteEvent(
                    note=note,
                    start=round(start_sec, 4),
                    end=round(end_sec, 4),
                    velocity=round(vel, 2),
                ))

    # Close any still active notes
    for note, (start_sec, vel) in active_notes.items():
        events.append(NoteEvent(
            note=note,
            start=round(start_sec, 4),
            end=round(start_sec + 0.2, 4),
            velocity=round(vel, 2),
        ))

    events.sort(key=lambda e: (e["start"], e["note"]))
    return events


def _parse_midi_via_subshell(midi_path: Path, venv_python: Path) -> list[NoteEvent]:
    """Delegate MIDI parsing to .venv Python where mido is installed."""
    import subprocess
    import tempfile

    tmp_out = Path(tempfile.mktemp(suffix=".json"))
    script_content = f"""
import json, mido
mid = mido.MidiFile(r"{midi_path}")
events = []
active = {{}}
t = 0.0
for msg in mid:
    t += msg.time
    if msg.type == 'note_on' and msg.velocity > 0:
        if 21 <= msg.note <= 108:
            active[msg.note] = (t, float(msg.velocity))
    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
        if msg.note in active:
            st, vel = active.pop(msg.note)
            ed = max(t, st + 0.05)
            events.append({{'note': msg.note, 'start': round(st, 4), 'end': round(ed, 4), 'velocity': round(vel, 2)}})

for note, (st, vel) in active.items():
    events.append({{'note': note, 'start': round(st, 4), 'end': round(st + 0.2, 4), 'velocity': round(vel, 2)}})

events.sort(key=lambda e: (e['start'], e['note']))
with open(r"{tmp_out}", "w", encoding="utf-8") as f:
    json.dump(events, f)
"""
    cmd = [str(venv_python), "-c", script_content]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0 and tmp_out.exists():
            with open(tmp_out, "r", encoding="utf-8") as f:
                data = json.load(f)
            tmp_out.unlink(missing_ok=True)
            return data
    except Exception as e:
        print(f"[Warning] Subshell MIDI parsing failed ({e}).", file=sys.stderr)
    finally:
        tmp_out.unlink(missing_ok=True)
    return []


def save_ray_notes(events: list[NoteEvent], path: str | Path) -> None:
    """HTMLビューアー用 JSON ファイルとして保存する。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def load_ray_notes(path: str | Path) -> list[NoteEvent]:
    """JSON ファイルからノートイベントを読み込む。"""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "notes" in data:
        data = data["notes"]
    return parse_raw_events(data)
