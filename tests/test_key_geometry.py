from pipeline.vision.finger_mapper import FingerKeyMapper
from pipeline.vision.key_geometry import (
    MAX_MIDI,
    MIN_MIDI,
    NUM_BLACK_KEYS,
    NUM_WHITE_KEYS,
    black_key_span_u,
    is_black,
    note_to_u,
    u_to_note,
    white_index,
)


def test_key_counts():
    blacks = sum(1 for n in range(MIN_MIDI, MAX_MIDI + 1) if is_black(n))
    assert blacks == NUM_BLACK_KEYS
    assert (MAX_MIDI - MIN_MIDI + 1) - blacks == NUM_WHITE_KEYS


def test_round_trip_all_notes():
    for n in range(MIN_MIDI, MAX_MIDI + 1):
        v = 0.2 if is_black(n) else 0.9
        assert u_to_note(note_to_u(n), v) == n, n


def test_white_index_known_values():
    assert white_index(21) == 0    # A0
    assert white_index(23) == 1    # B0
    assert white_index(24) == 2    # C1
    assert white_index(22) == 0    # A#0 -> white key to its left (A0)
    assert white_index(25) == 2    # C#1 -> C1
    assert white_index(108) == 51  # C8


def test_black_key_lies_between_its_white_neighbours():
    for n in range(MIN_MIDI, MAX_MIDI + 1):
        if is_black(n):
            left = note_to_u(n - 1)
            right = note_to_u(n + 1)
            assert left < note_to_u(n) < right, n
            l, r = black_key_span_u(n)
            assert l < note_to_u(n) < r


def test_black_vs_white_selected_by_v():
    u = note_to_u(25)  # C#1
    assert u_to_note(u, 0.2) == 25   # back of the key -> black
    assert u_to_note(u, 0.9) == 24   # front of the key -> white C1
    assert u_to_note(u, None) == 24


def test_clamping():
    assert u_to_note(-0.5, 0.9) == MIN_MIDI
    assert u_to_note(1.5, 0.9) == MAX_MIDI


def test_map_wrists_uses_landmark_zero():
    mapper = FingerKeyMapper(((0, 0), (100, 0), (100, 100), (0, 100)))
    hands = [
        {"timestamp": 1.0, "hand_id": 0, "landmarks": [(50, 50), (60, 60)]},
        {"timestamp": 2.0, "hand_id": 1, "landmarks": [(0, 0)]},
        {"timestamp": 3.0, "hand_id": 1},  # no landmarks -> skipped
    ]
    res = mapper.map_wrists(hands)
    assert len(res) == 2
    assert abs(res[0]["u"] - 0.5) < 1e-2 and res[0]["hand_id"] == 0
    assert abs(res[1]["u"]) < 1e-2 and res[1]["hand_id"] == 1
