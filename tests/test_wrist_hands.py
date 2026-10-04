"""Tests for wrist-position based hand assignment for unmatched audio notes."""

import pytest
from pipeline.integration.json_builder import build_ray_notes, interpolate_wrist_u
from pipeline.vision.key_geometry import note_to_u


def test_wrist_hand_assignment_far_right():
    """(a) Note far right, right wrist near, left wrist far -> 'R', wrist source."""
    # Note 100 (high pitch, right side). u_note ~ 0.95
    audio_events = [{"note": 100, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    # Right wrist (hand_id=1) at u=0.9, Left wrist (hand_id=0) at u=0.5
    wrist_events = [
        {"timestamp": 1.0, "hand_id": 0, "u": 0.5, "v": 0.5},
        {"timestamp": 1.0, "hand_id": 1, "u": 0.9, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    assert len(notes) == 1
    assert notes[0]["hand"] == "R"
    assert notes[0]["hand_source"] == "wrist"
    assert notes[0]["finger"] == 0
    assert notes[0]["confidence"] == 0.25


def test_wrist_cross_hand():
    """(b) Cross-hand: Left wrist at u=0.9, Right wrist at u=0.2, note at u~0.88 -> 'L'."""
    # Note 90 (u ~ 0.88)
    audio_events = [{"note": 90, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    # Left wrist (hand_id=0) at u=0.9, Right wrist (hand_id=1) at u=0.2
    wrist_events = [
        {"timestamp": 1.0, "hand_id": 0, "u": 0.9, "v": 0.5},
        {"timestamp": 1.0, "hand_id": 1, "u": 0.2, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    assert len(notes) == 1
    assert notes[0]["hand"] == "L"
    assert notes[0]["hand_source"] == "wrist"
    assert notes[0]["confidence"] == 0.25


def test_wrist_single_hand_near():
    """(c) Only one hand visible and near -> that hand."""
    # Note 60 (u ~ 0.5)
    audio_events = [{"note": 60, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    # Only Right wrist (hand_id=1) at u=0.55 (dist 0.05 <= 0.35)
    wrist_events = [
        {"timestamp": 1.0, "hand_id": 1, "u": 0.55, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    assert len(notes) == 1
    assert notes[0]["hand"] == "R"
    assert notes[0]["hand_source"] == "wrist"
    assert notes[0]["confidence"] == 0.25


def test_wrist_far_falls_back_to_proximity():
    """(d) Wrist sample older than max_gap -> falls back to proximity."""
    # Note 60 (u ~ 0.5)
    audio_events = [{"note": 60, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    # Only Right wrist at t=0.0 (gap 1.0s, max_gap=1.0). 
    # Note: "older than max_gap" implies strictly > max_gap? 
    # Spec: "return None if nearest sample is farther than max_gap_sec".
    # If gap == max_gap, it is NOT farther. So it returns u.
    # Let's test gap > max_gap.
    wrist_events = [
        {"timestamp": 0.0, "hand_id": 1, "u": 0.5, "v": 0.5},
    ]
    # Start 1.0, ts 0.0, gap 1.0. max_gap 1.0. 1.0 is not > 1.0. So it returns u.
    # Let's make gap 1.1.
    wrist_events = [
        {"timestamp": -0.1, "hand_id": 1, "u": 0.5, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    # Should fall back to proximity. last_l=48, last_r=72.
    # abs(60-48)=12, abs(60-72)=12. Tie -> L.
    assert notes[0]["hand"] == "L"
    assert notes[0]["hand_source"] == "proximity"
    assert notes[0]["confidence"] == 0.0


def test_wrist_av_offset():
    """(e) av_offset shifts wrist timestamps."""
    # Note 60, start 1.0.
    # Wrist at t=0.8. av_offset=0.2 -> adj_ts=1.0.
    audio_events = [{"note": 60, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    wrist_events = [
        {"timestamp": 0.8, "hand_id": 1, "u": 0.5, "v": 0.5},
    ]
    
    # Without offset, gap is 0.2. With offset 0.2, gap is 0.
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, av_offset_sec=0.2, wrist_events=wrist_events)
    notes = res["notes"]
    
    assert notes[0]["hand"] == "R"
    assert notes[0]["hand_source"] == "wrist"
    assert notes[0]["confidence"] == 0.25


def test_wrist_interpolation():
    """(f) Interpolation between two samples."""
    # Note 60, start 1.0.
    # Left wrist: t=0.5, u=0.4; t=1.5, u=0.6.
    # At t=1.0, interpolated u = 0.5.
    # u_note for 60 is ~0.5.
    # Right wrist: far.
    
    audio_events = [{"note": 60, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = []
    
    wrist_events = [
        {"timestamp": 0.5, "hand_id": 0, "u": 0.4, "v": 0.5},
        {"timestamp": 1.5, "hand_id": 0, "u": 0.6, "v": 0.5},
        {"timestamp": 1.0, "hand_id": 1, "u": 0.9, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    # u_note ~ 0.5. u_left = 0.5. u_right = 0.9.
    # dist_left = 0.0, dist_right = 0.4.
    # Left wins.
    assert notes[0]["hand"] == "L"
    assert notes[0]["hand_source"] == "wrist"


def test_vision_match_priority():
    """(g) Notes WITH vision match keep vision hand and hand_source == 'vision'."""
    audio_events = [{"note": 60, "start": 1.0, "end": 1.5, "velocity": 90.0}]
    vision_events = [{"note": 60, "finger": 1, "hand": "R", "timestamp": 1.0, "v": 0.9}]
    
    # Wrist says Left, Vision says Right. Vision wins.
    wrist_events = [
        {"timestamp": 1.0, "hand_id": 0, "u": 0.5, "v": 0.5},
        {"timestamp": 1.0, "hand_id": 1, "u": 0.9, "v": 0.5},
    ]
    
    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05, wrist_events=wrist_events)
    notes = res["notes"]
    
    assert notes[0]["hand"] == "R"
    assert notes[0]["hand_source"] == "vision"
    assert notes[0]["finger"] == 1
    assert notes[0]["confidence"] > 0.9