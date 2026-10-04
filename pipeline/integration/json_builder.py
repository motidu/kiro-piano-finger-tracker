"""Integration module merging audio NoteEvents and vision finger events.

Merges normalized audio notes (from midi_parser) with vision finger mappings
(from finger_mapper) to produce a unified ray_notes.json structure.
"""

from __future__ import annotations

import json
import bisect
from pathlib import Path
from typing import TypedDict

from pipeline.vision.key_geometry import note_to_u


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
    hand_source: str


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


def interpolate_wrist_u(wrist_events: list[dict], hand_id: int, t: float, max_gap_sec: float = 1.0, av_offset_sec: float = 0.0) -> float | None:
    """Interpolate wrist u coordinate for a given hand_id at time t.
    
    Uses bisect on pre-sorted per-hand list. Returns None if nearest sample
    is farther than max_gap_sec.
    """
    # Filter events for the specific hand_id
    hand_events = [e for e in wrist_events if e["hand_id"] == hand_id]
    if not hand_events:
        return None
    
    # Apply av_offset_sec to timestamps
    adjusted_events = [(e["timestamp"] + av_offset_sec, e["u"]) for e in hand_events]
    # Sort by timestamp (assumed pre-sorted in most cases, but ensure)
    adjusted_events.sort(key=lambda x: x[0])
    
    timestamps = [e[0] for e in adjusted_events]
    
    # Find insertion point
    idx = bisect.bisect_left(timestamps, t)
    
    # Check nearest sample distance
    candidates = []
    if idx < len(adjusted_events):
        candidates.append((adjusted_events[idx][0], adjusted_events[idx][1]))
    if idx > 0:
        candidates.append((adjusted_events[idx-1][0], adjusted_events[idx-1][1]))
    
    if not candidates:
        return None
        
    # Find closest in time
    closest = min(candidates, key=lambda c: abs(c[0] - t))
    
    if abs(closest[0] - t) > max_gap_sec:
        return None
    
    # Linear interpolation between prev and next
    if idx < len(adjusted_events) and idx > 0:
        prev_t, prev_u = adjusted_events[idx-1]
        next_t, next_u = adjusted_events[idx]
        
        # Clamp to nearest sample if outside range (handled by candidates above, 
        # but for interpolation logic inside range):
        if prev_t <= t <= next_t:
            if next_t == prev_t:
                return prev_u
            ratio = (t - prev_t) / (next_t - prev_t)
            return prev_u + ratio * (next_u - prev_u)
        
    # If closest is outside the bracketing pair (e.g. t < first or t > last), 
    # the 'candidates' logic above picks the single nearest.
    # If t is exactly on a sample, return it.
    return closest[1]


def build_ray_notes(
    audio_events: list[dict],
    vision_events: list[dict],
    tolerance_sec: float = 0.05,
    av_offset_sec: float = 0.0,
    title: str = "Integrated Piano Notes",
    wrist_events: list[dict] | None = None,
) -> dict:
    """Merge audio NoteEvents with vision finger events into unified JSON structure.

    Args:
        audio_events: Normalized NoteEvent list from midi_parser.
        vision_events: VisionEvent list from finger_mapper.
        tolerance_sec: Time matching tolerance in seconds (default 0.05 = 50ms).
        av_offset_sec: Audio/Video sync offset (added to vision timestamp).
        title: Meta title string.
        wrist_events: Optional list of wrist position events for hand assignment.

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
            hand_source = "vision"
        else:
            finger = 0
            # Determine hand using wrist events if available
            hand = None
            hand_source = "proximity"
            confidence = 0.0
            
            if wrist_events:
                u_note = note_to_u(note)
                u_left = interpolate_wrist_u(wrist_events, 0, start, max_gap_sec=1.0, av_offset_sec=av_offset_sec)
                u_right = interpolate_wrist_u(wrist_events, 1, start, max_gap_sec=1.0, av_offset_sec=av_offset_sec)
                
                if u_left is not None and u_right is not None:
                    dist_l = abs(u_note - u_left)
                    dist_r = abs(u_note - u_right)
                    if dist_l < dist_r:
                        hand = "L"
                        hand_source = "wrist"
                        confidence = 0.25
                    elif dist_r < dist_l:
                        hand = "R"
                        hand_source = "wrist"
                        confidence = 0.25
                    else:
                        # Tie: keep previous-note proximity rule
                        dist_l_note = abs(note - last_l_note)
                        dist_r_note = abs(note - last_r_note)
                        hand = "L" if dist_l_note <= dist_r_note else "R"
                        hand_source = "proximity"
                elif u_left is not None:
                    dist = abs(u_note - u_left)
                    if dist <= 0.35:
                        hand = "L"
                        hand_source = "wrist"
                        confidence = 0.25
                    else:
                        # Fall back to proximity
                        dist_l_note = abs(note - last_l_note)
                        dist_r_note = abs(note - last_r_note)
                        hand = "L" if dist_l_note <= dist_r_note else "R"
                        hand_source = "proximity"
                elif u_right is not None:
                    dist = abs(u_note - u_right)
                    if dist <= 0.35:
                        hand = "R"
                        hand_source = "wrist"
                        confidence = 0.25
                    else:
                        # Fall back to proximity
                        dist_l_note = abs(note - last_l_note)
                        dist_r_note = abs(note - last_r_note)
                        hand = "L" if dist_l_note <= dist_r_note else "R"
                        hand_source = "proximity"
                else:
                    # No wrists available, use proximity
                    dist_l_note = abs(note - last_l_note)
                    dist_r_note = abs(note - last_r_note)
                    hand = "L" if dist_l_note <= dist_r_note else "R"
                    hand_source = "proximity"
            else:
                # No wrist events, use proximity
                dist_l_note = abs(note - last_l_note)
                dist_r_note = abs(note - last_r_note)
                hand = "L" if dist_l_note <= dist_r_note else "R"
                hand_source = "proximity"

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
            hand_source=hand_source,
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
