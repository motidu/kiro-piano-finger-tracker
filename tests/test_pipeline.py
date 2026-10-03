"""Integration tests for end-to-end piano finger tracking pipeline."""

import json
import pytest
from pathlib import Path

from pipeline.integration.json_builder import (
    build_ray_notes,
    save_integrated_json,
    load_integrated_json,
    _infer_hand,
    _normalize_hand,
)
from pipeline.main import run_pipeline, parse_quad_argument


def test_infer_hand():
    """Verify hand inference from MIDI note: < 60 is L, >= 60 is R."""
    assert _infer_hand(59) == "L"
    assert _infer_hand(60) == "R"
    assert _infer_hand(21) == "L"
    assert _infer_hand(108) == "R"


def test_normalize_hand():
    """Verify hand normalization for int, str, and fallback."""
    assert _normalize_hand(0, 60) == "L"
    assert _normalize_hand(1, 60) == "R"
    assert _normalize_hand("l", 60) == "L"
    assert _normalize_hand("left", 60) == "L"
    assert _normalize_hand("r", 60) == "R"
    assert _normalize_hand("right", 60) == "R"
    assert _normalize_hand("unknown", 50) == "L"
    assert _normalize_hand("unknown", 70) == "R"


def test_build_ray_notes_matching():
    """Verify matching of audio and vision events within tolerance window."""
    audio_events = [
        {"note": 60, "start": 1.0, "end": 1.5, "velocity": 100.0},
        {"note": 64, "start": 2.0, "end": 2.5, "velocity": 90.0},
    ]

    vision_events = [
        # Match for note 60: at 1.02s (diff = 20ms <= 50ms)
        {"note": 60, "finger": 1, "hand": "R", "timestamp": 1.02, "v": 0.8},
        # Candidate 1 for note 64: at 1.98s, v=0.6
        {"note": 64, "finger": 3, "hand": "R", "timestamp": 1.98, "v": 0.6},
        # Candidate 2 for note 64: at 2.01s, v=0.95 (deeper press -> should win)
        {"note": 64, "finger": 3, "hand": "R", "timestamp": 2.01, "v": 0.95},
    ]

    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05)
    notes = res["notes"]

    assert len(notes) == 2
    # Note 60
    assert notes[0]["note"] == 60
    assert notes[0]["finger"] == 1
    assert notes[0]["hand"] == "R"
    assert notes[0]["confidence"] > 0.5

    # Note 64 - candidate 2 won
    assert notes[1]["note"] == 64
    assert notes[1]["finger"] == 3
    assert notes[1]["hand"] == "R"
    assert notes[1]["confidence"] > 0.7


def test_build_ray_notes_unmatched_audio_fallback():
    """Verify that audio note without vision match gets finger=0 and pitch-inferred hand."""
    audio_events = [
        {"note": 48, "start": 0.5, "end": 1.0, "velocity": 80.0},  # Low note -> L
        {"note": 72, "start": 1.5, "end": 2.0, "velocity": 85.0},  # High note -> R
    ]
    vision_events = []  # No vision events

    res = build_ray_notes(audio_events, vision_events, tolerance_sec=0.05)
    notes = res["notes"]

    assert len(notes) == 2
    assert notes[0]["finger"] == 0
    assert notes[0]["hand"] == "L"
    assert notes[0]["confidence"] == 0.0

    assert notes[1]["finger"] == 0
    assert notes[1]["hand"] == "R"
    assert notes[1]["confidence"] == 0.0


def test_save_and_load_integrated_json(tmp_path):
    """Verify saving and reloading integrated json file."""
    audio_events = [{"note": 60, "start": 0.5, "end": 1.0, "velocity": 90.0}]
    vision_events = [{"note": 60, "finger": 1, "hand": "R", "timestamp": 0.51, "v": 0.9}]

    data = build_ray_notes(audio_events, vision_events)
    out_file = tmp_path / "integrated.json"

    save_integrated_json(data, out_file)
    assert out_file.exists()

    loaded = load_integrated_json(out_file)
    assert loaded["meta"]["total_notes"] == 1
    assert loaded["notes"][0]["note"] == 60
    assert loaded["notes"][0]["finger"] == 1


def test_parse_quad_argument():
    """Verify parsing 8 floats and JSON quad formats."""
    # Comma-separated 8 floats
    quad_str = "0.1, 0.7, 0.9, 0.7, 0.95, 0.95, 0.05, 0.95"
    q1 = parse_quad_argument(quad_str)
    assert len(q1) == 4
    assert q1[0] == (0.1, 0.7)
    assert q1[3] == (0.05, 0.95)

    # JSON format
    json_quad = "[[0.1, 0.7], [0.9, 0.7], [0.95, 0.95], [0.05, 0.95]]"
    q2 = parse_quad_argument(json_quad)
    assert len(q2) == 4
    assert q2 == q1

    # Invalid length raises ValueError
    with pytest.raises(ValueError):
        parse_quad_argument("0.1, 0.2, 0.3")


def test_run_pipeline_end_to_end(tmp_path):
    """Verify run_pipeline with mock audio and vision inputs."""
    audio_events = [
        {"note": 60, "start": 0.5, "end": 1.0, "velocity": 95.0},
        {"note": 62, "start": 1.0, "end": 1.5, "velocity": 90.0},
    ]
    hands_data = [
        {
            "timestamp": 0.52,
            "hand_id": 1,
            "fingers": [
                {"x": 50, "y": 80, "finger_id": 1}
            ],
        },
        {
            "timestamp": 1.01,
            "hand_id": 1,
            "fingers": [
                {"x": 52, "y": 80, "finger_id": 2}
            ],
        },
    ]

    out_json = tmp_path / "ray_notes.json"
    result = run_pipeline(
        audio_events=audio_events,
        hands_data=hands_data,
        quad=((0, 0), (100, 0), (100, 100), (0, 100)),
        output_path=out_json,
        tolerance_sec=0.05,
        title="Test Pipeline",
    )

    assert out_json.exists()
    assert result["meta"]["title"] == "Test Pipeline"
    assert len(result["notes"]) == 2
    assert result["notes"][0]["note"] == 60
