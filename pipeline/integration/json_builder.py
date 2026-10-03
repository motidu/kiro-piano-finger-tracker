"""Integration module merging audio NoteEvents and vision finger events.

Merges normalized audio notes (from midi_parser) with vision finger mappings
(from finger_mapper) to produce a unified ray_notes.json structure.

Time matching uses a tolerance window (default ±50ms). For each audio note,
the vision event with the highest `v` coordinate (deepest press) within the
window and matching MIDI note is selected. Unmatched audio notes receive
finger=0 and hand inferred from pitch.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict


class NoteEvent(TypedDict):
    note: int
    start: float
    end: float
    velocity: float


class VisionEvent(TypedDict):
    timestamp: float
    note: int
    finger: int
    hand: int | str
    u: float
    v: float


class IntegratedNote(TypedDict):
    note: int
    start: float
    end: float
    finger: int
    hand: str
    velocity: float
    confidence: float


def _infer_hand(note: int) -> str:
    """Infer hand from pitch: lower notes -> Left, higher -> Right."""
    return "L" if note < 60 else "R"


def _normalize_hand(hand_val: int | str, note: int) -> str:
    """Normalize hand representation to 'L' or 'R'."""
    if isinstance(hand_val, int):
        return "L" if hand_val == 0 else "R"
    if isinstance(hand_val, str):
        h = hand_val.strip().upper()
        if h in ("L", "LEFT", "0"):
            return "L"
        if h in ("R", "RIGHT", "1"):
            return "R"
    return _infer_hand(note)


def build_ray_notes(
    audio_events: list[dict],
    vision_events: list[dict],
    tolerance_sec: float = 0.05,
    title: str = "Integrated Piano Notes",
) -> dict:
    """Merge audio NoteEvents with vision finger events into unified JSON structure.

    Args:
        audio_events: Normalized NoteEvent list from midi_parser.
        vision_events: VisionEvent list from finger_mapper.
        tolerance_sec: Time matching tolerance in seconds (default 0.05 = 50ms).
        title: Meta title string.

    Returns:
        Dictionary matching web/data/ray_notes.json schema.
    """
    # Pre-index vision events by note for fast lookup
    vision_by_note: dict[int, list[dict]] = {}
    for ve in vision_events:
        note_id = int(ve["note"])
        if note_id not in vision_by_note:
            vision_by_note[note_id] = []
        vision_by_note[note_id].append(ve)

    # Sort vision events per note by timestamp
    for note_id in vision_by_note:
        vision_by_note[note_id].sort(key=lambda e: float(e["timestamp"]))

    merged_notes: list[IntegratedNote] = []

    for audio in audio_events:
        note = int(audio["note"])
        start = float(audio["start"])
        end = float(audio["end"])
        velocity = float(audio.get("velocity", 90.0))

        # Search vision events in [start - tolerance, start + tolerance]
        candidates = vision_by_note.get(note, [])
        best_vision: dict | None = None
        best_v = -1.0

        for ve in candidates:
            ts = float(ve["timestamp"])
            if start - tolerance_sec <= ts <= start + tolerance_sec:
                v_val = float(ve.get("v", 0.5))
                if v_val > best_v:
                    best_v = v_val
                    best_vision = ve

        if best_vision is not None:
            finger = int(best_vision["finger"])
            hand = _normalize_hand(best_vision["hand"], note)
            # Confidence based on proximity to note start
            time_diff = abs(float(best_vision["timestamp"]) - start)
            confidence = max(0.0, 1.0 - (time_diff / tolerance_sec))
        else:
            finger = 0
            hand = _infer_hand(note)
            confidence = 0.0

        merged_notes.append(IntegratedNote(
            note=note,
            start=round(start, 4),
            end=round(end, 4),
            finger=finger,
            hand=hand,
            velocity=round(velocity, 2),
            confidence=round(confidence, 4),
        ))

    # Compute duration
    if merged_notes:
        duration_sec = max(n["end"] for n in merged_notes)
    else:
        duration_sec = 0.0

    result = {
        "meta": {
            "title": title,
            "duration_sec": round(duration_sec, 4),
            "time_tolerance_ms": int(tolerance_sec * 1000),
            "total_notes": len(merged_notes),
        },
        "notes": merged_notes,
    }

    return result


def save_integrated_json(data: dict, output_path: str | Path) -> None:
    """Save integrated ray notes JSON to file with UTF-8 encoding.

    Args:
        data: Dictionary produced by build_ray_notes.
        output_path: Destination file path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_integrated_json(path: str | Path) -> dict:
    """Load integrated ray notes JSON from file.

    Args:
        path: Source file path.

    Returns:
        Dictionary matching ray_notes.json schema.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
