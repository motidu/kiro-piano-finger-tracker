"""Integration module merging audio NoteEvents and vision finger events.

Merges normalized audio notes (from midi_parser) with vision finger mappings
(from finger_mapper) to produce a unified ray_notes.json structure.
"""

from __future__ import annotations

import json
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


def _normalize_hand(hand_val: int | str, note: int, last_l: int, last_r: int) -> str:
    """Normalize hand representation to 'L' or 'R'.
    Falls back to proximity to last known hand positions if unknown.
    """
    if isinstance(hand_val, int):
        return "L" if hand_val == 0 else "R"
    if isinstance(hand_val, str):
        h = hand_val.strip().upper()
        if h in ("L", "LEFT", "0"):
            return "L"
        if h in ("R", "RIGHT", "1"):
            return "R"
    return "L" if abs(note - last_l) <= abs(note - last_r) else "R"


def build_ray_notes(
    audio_events: list[dict],
    vision_events: list[dict],
    tolerance_sec: float = 0.05,
    av_offset_sec: float = 0.0,
    title: str = "Integrated Piano Notes",
) -> dict:
    """Merge audio NoteEvents with vision finger events into unified JSON structure.

    Args:
        audio_events: Normalized NoteEvent list from midi_parser.
        vision_events: VisionEvent list from finger_mapper.
        tolerance_sec: Time matching tolerance in seconds (default 0.05 = 50ms).
        av_offset_sec: Audio/Video sync offset (added to vision timestamp).
        title: Meta title string.

    Returns:
        Dictionary matching web/data/ray_notes.json schema.
    """
    # Pre-index vision events by note for fast lookup. Store (original_index, event)
    vision_by_note: dict[int, list[tuple[int, dict]]] = {}
    for i, ve in enumerate(vision_events):
        note_id = int(ve["note"])
        if note_id not in vision_by_note:
            vision_by_note[note_id] = []
        vision_by_note[note_id].append((i, ve))

    # Sort vision events per note by timestamp
    for note_id in vision_by_note:
        vision_by_note[note_id].sort(key=lambda item: float(item[1]["timestamp"]))

    merged_notes: list[IntegratedNote] = []
    consumed_vision: set[int] = set()

    # Dynamic state for context-aware hand fallback (start at typical resting positions)
    last_l_note = 48  # C3
    last_r_note = 72  # C5

    for audio in audio_events:
        note = int(audio["note"])
        start = float(audio["start"])
        end = float(audio["end"])
        velocity = float(audio.get("velocity", 90.0))

        # Search vision events in [start - tolerance, start + tolerance]
        candidates = vision_by_note.get(note, [])
        best_vision: dict | None = None
        best_idx = -1
        best_v = -1.0

        for v_idx, ve in candidates:
            if v_idx in consumed_vision:
                continue  # Prevent double-booking (trill protection)

            # Apply A/V offset to vision timestamp
            adj_ts = float(ve["timestamp"]) + av_offset_sec
            if start - tolerance_sec <= adj_ts <= start + tolerance_sec:
                v_val = float(ve.get("v", 0.5))
                if v_val > best_v:
                    best_v = v_val
                    best_vision = ve
                    best_idx = v_idx

        if best_vision is not None:
            consumed_vision.add(best_idx)
            finger = int(best_vision["finger"])
            hand = _normalize_hand(best_vision["hand"], note, last_l_note, last_r_note)
            
            adj_ts = float(best_vision["timestamp"]) + av_offset_sec
            time_diff = abs(adj_ts - start)
            confidence = max(0.0, 1.0 - (time_diff / tolerance_sec))
        else:
            finger = 0
            # Context-aware fallback: assign to the hand closest to its last known position
            dist_l = abs(note - last_l_note)
            dist_r = abs(note - last_r_note)
            hand = "L" if dist_l <= dist_r else "R"
            confidence = 0.0

        # Update dynamic hand positions
        if hand == "L":
            last_l_note = note
        else:
            last_r_note = note

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
            "av_offset_sec": round(av_offset_sec, 4),
            "total_notes": len(merged_notes),
        },
        "notes": merged_notes,
    }

    return result


def save_integrated_json(data: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_integrated_json(path: str | Path) -> dict:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
