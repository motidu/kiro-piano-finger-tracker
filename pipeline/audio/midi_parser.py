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


def save_ray_notes(events: list[NoteEvent], path: str | Path) -> None:
    """HTMLビューア用の JSON ファイルとして保存する。"""
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
