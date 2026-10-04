"""Real piano key geometry (88 keys, MIDI 21..108) for an OVERHEAD camera.

Coordinates
-----------
u : 0..1 left -> right across the 52 white keys (each white key is 1/52 wide).
v : 0..1 across the keyboard quad as solved by ``FingerKeyMapper._solve_bilinear``.
    The quad order is TL, TR, BR, BL, so v=0 is the TOP edge of the image
    (the BACK of the keyboard, where black keys sit) and v=1 is the BOTTOM edge
    (the FRONT, nearest to the player).

The Web viewer (web/js/key_geometry.js) uses the same u definition so that
the pipeline and the visualizer agree on where every key is.
"""

from __future__ import annotations

from typing import Optional, Tuple

MIN_MIDI = 21   # A0
MAX_MIDI = 108  # C8
NUM_WHITE_KEYS = 52
NUM_BLACK_KEYS = 36

BLACK_PITCH_CLASSES = frozenset({1, 3, 6, 8, 10})

# Offset of a black key centre from the boundary between its two neighbouring
# white keys, in white-key widths (real pianos group black keys 2+3).
BLACK_OFFSETS = {1: -0.10, 3: 0.10, 6: -0.15, 8: 0.0, 10: 0.15}

BLACK_KEY_WIDTH = 0.58  # in white-key widths

# Black keys occupy the back part of the key (v small). At or below this v a
# fingertip may be on a black key; above it the fingertip is on a white key.
BLACK_KEY_V_MAX = 0.60

# ---- precomputed tables --------------------------------------------------
_WHITE_INDEX = {}      # note -> white index (black: white key to its LEFT)
_WHITE_NOTES = []      # white index -> MIDI note
_BLACK_NOTES = []      # sorted black MIDI notes

_count = 0
for _n in range(MIN_MIDI, MAX_MIDI + 1):
    if (_n % 12) in BLACK_PITCH_CLASSES:
        _WHITE_INDEX[_n] = _count - 1
        _BLACK_NOTES.append(_n)
    else:
        _WHITE_INDEX[_n] = _count
        _WHITE_NOTES.append(_n)
        _count += 1

assert len(_WHITE_NOTES) == NUM_WHITE_KEYS and len(_BLACK_NOTES) == NUM_BLACK_KEYS


def is_black(note: int) -> bool:
    return (note % 12) in BLACK_PITCH_CLASSES


def white_index(note: int) -> int:
    """Index (0..51) of the white key; for a black key, the white key to its left."""
    return _WHITE_INDEX[note]


def note_to_u(note: int) -> float:
    """u of the CENTRE of the key."""
    idx = _WHITE_INDEX[note]
    if not is_black(note):
        return (idx + 0.5) / NUM_WHITE_KEYS
    return (idx + 1 + BLACK_OFFSETS[note % 12]) / NUM_WHITE_KEYS


def black_key_span_u(note: int) -> Tuple[float, float]:
    """(u_left, u_right) of a black key."""
    if not is_black(note):
        raise ValueError(f"note {note} is not a black key")
    centre = note_to_u(note)
    half = BLACK_KEY_WIDTH / NUM_WHITE_KEYS / 2.0
    return (centre - half, centre + half)


_BLACK_SPANS = [(black_key_span_u(n), n) for n in _BLACK_NOTES]


def u_to_note(u: float, v: Optional[float] = None) -> int:
    """MIDI note under the point (u, v). With v=None only white keys are returned."""
    u = max(0.0, min(1.0, u))
    if v is not None and v <= BLACK_KEY_V_MAX:
        for (left, right), note in _BLACK_SPANS:
            if left <= u <= right:
                return note
    idx = min(NUM_WHITE_KEYS - 1, int(u * NUM_WHITE_KEYS))
    return _WHITE_NOTES[idx]


if __name__ == "__main__":
    bad = [n for n in range(MIN_MIDI, MAX_MIDI + 1)
           if u_to_note(note_to_u(n), 0.2 if is_black(n) else 0.9) != n]
    print("Self-check passed." if not bad else f"Self-check failed: {bad}")
