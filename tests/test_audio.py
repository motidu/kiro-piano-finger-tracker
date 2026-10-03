import pytest
from pathlib import Path
from pipeline.audio.midi_parser import (
    freq_to_midi,
    parse_raw_events,
    save_ray_notes,
    load_ray_notes,
    MIN_NOTE,
    MAX_NOTE,
)

def test_freq_to_midi():
    """周波数から MIDI ノート番号への変換精度を検証"""
    assert freq_to_midi(440.0) == 69  # A4 = 440Hz
    assert freq_to_midi(261.63) == 60 # C4 (Middle C) ≈ 261.63Hz
    assert freq_to_midi(27.5) == 21   # A0 (Lowest key) = 27.5Hz
    assert freq_to_midi(4186.01) == 108 # C8 (Highest key) ≈ 4186.01Hz

def test_parse_raw_events_clamping_and_sorting():
    """88鍵の範囲外除外と、開始時間順のソートを検証"""
    raw = [
        {"note": 64, "start": 1.5, "end": 2.0},
        {"note": 60, "start": 0.5, "end": 1.0},
        {"note": 10, "start": 0.1, "end": 0.5}, # 21未満 (除外対象)
        {"note": 120, "start": 0.2, "end": 0.5}, # 108超 (除外対象)
        {"pitch": 440.0, "onset": 0.8, "duration": 0.5}, # A4 (69)
    ]

    events = parse_raw_events(raw)
    assert len(events) == 3
    # ソート順: start が 0.5 -> 0.8 -> 1.5
    assert events[0]["note"] == 60
    assert events[0]["start"] == 0.5
    assert events[1]["note"] == 69
    assert events[1]["start"] == 0.8
    assert events[2]["note"] == 64
    assert events[2]["start"] == 1.5

def test_save_and_load_ray_notes(tmp_path):
    """JSON 保存と再読込の整合性を検証"""
    sample = [
        {"note": 60, "start": 0.5, "end": 1.0, "velocity": 100.0},
        {"note": 64, "start": 1.0, "end": 1.5, "velocity": 90.0},
    ]
    out_file = tmp_path / "test_notes.json"
    save_ray_notes(sample, out_file)
    assert out_file.exists()

    loaded = load_ray_notes(out_file)
    assert len(loaded) == 2
    assert loaded[0]["note"] == 60
    assert loaded[1]["note"] == 64
