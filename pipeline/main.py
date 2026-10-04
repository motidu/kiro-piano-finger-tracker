"""End-to-end pipeline orchestrator for piano finger tracking.

Combines MIDI transcription parsing, vision MediaPipe fingertip tracking,
inverse bilinear 88-key mapping, and temporal integration into ray_notes.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Reconfigure stdout to UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure repository root is on sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.audio.midi_parser import (
    parse_midi_file,
    parse_raw_events,
)
from pipeline.audio.transcriber import (
    extract_audio_from_video,
    detect_wav_notes_simple,
)
from pipeline.vision.finger_mapper import FingerKeyMapper
from pipeline.vision.video_tracker import extract_hands_from_video
from pipeline.integration.json_builder import (
    build_ray_notes,
    save_integrated_json,
    load_integrated_json,
)

DEFAULT_QUAD: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]] = (
    (0.1, 0.7),
    (0.9, 0.7),
    (0.95, 0.95),
    (0.05, 0.95),
)


def parse_quad_argument(quad_str: str) -> Tuple[Tuple[float, float], ...]:
    """Parse comma-separated 8 floats or JSON 4 points into quad tuple."""
    quad_str = quad_str.strip()
    if quad_str.startswith("["):
        points = json.loads(quad_str)
        return tuple((float(p[0]), float(p[1])) for p in points)
    parts = [float(x.strip()) for x in quad_str.split(",")]
    if len(parts) != 8:
        raise ValueError("Quad must contain exactly 8 float values (x0,y0,x1,y1,x2,y2,x3,y3)")
    return (
        (parts[0], parts[1]),
        (parts[2], parts[3]),
        (parts[4], parts[5]),
        (parts[6], parts[7]),
    )


def run_pipeline(
    video_path: str | Path | None = None,
    midi_path: str | Path | None = None,
    audio_path: str | Path | None = None,
    hands_data: List[Dict[str, Any]] | None = None,
    audio_events: List[Dict[str, Any]] | None = None,
    quad: Tuple[Tuple[float, float], ...] = DEFAULT_QUAD,
    output_path: str | Path = "web/data/ray_notes.json",
    tolerance_sec: float = 0.05,
    av_offset_sec: float = 0.0,
    title: str = "Piano Finger Tracking",
) -> Dict[str, Any]:
    """Execute end-to-end integration pipeline.

    Args:
        video_path: Input piano performance video file (.mp4/.mov).
        midi_path: Input MIDI file (.mid) containing note events.
        audio_path: Optional separate WAV file.
        hands_data: Pre-extracted hand landmark data (optional).
        audio_events: Pre-extracted audio NoteEvent list (optional).
        quad: 4 corner coordinates (TL, TR, BR, BL).
        output_path: Target destination path for ray_notes.json.
        tolerance_sec: Synchronization tolerance in seconds (default 50ms).
        av_offset_sec: Audio/Video sync offset in seconds (added to vision timestamps).
        title: Meta title for the dataset.

    Returns:
        Resulting ray_notes dictionary.
    """
    # 1. Resolve Audio / MIDI Note Events
    if audio_events is None:
        if midi_path is not None and Path(midi_path).exists():
            print(f"[Info] Parsing MIDI file: {midi_path}")
            audio_events = parse_midi_file(midi_path)
            print(f"[Info] Loaded {len(audio_events)} note events from MIDI.")
        elif audio_path is not None and Path(audio_path).exists():
            audio_wav = Path(audio_path)
            audio_events = detect_wav_notes_simple(audio_wav)
        elif video_path is not None and Path(video_path).exists():
            try:
                audio_wav = extract_audio_from_video(video_path)
                audio_events = detect_wav_notes_simple(audio_wav)
            except Exception as e:
                print(f"[Warning] Audio extraction from video failed ({e}).", file=sys.stderr)
                audio_events = []
        else:
            audio_events = []

    # 2. Resolve Vision Fingertip Events
    if hands_data is None:
        if video_path is not None and Path(video_path).exists():
            print(f"[Info] Extracting hand landmarks from video: {video_path}")
            hands_data = extract_hands_from_video(video_path)
            print(f"[Info] Extracted {len(hands_data)} hand frame records.")
        else:
            hands_data = []

    vision_mapper = FingerKeyMapper(quad)
    vision_events = vision_mapper.map_fingers_to_keys(hands_data, quad)
    print(f"[Info] Mapped {len(vision_events)} fingertip hit events.")

    # 3. Integrate & Merge
    integrated_data = build_ray_notes(
        audio_events=audio_events,
        vision_events=vision_events,
        tolerance_sec=tolerance_sec,
        av_offset_sec=av_offset_sec,
        title=title,
    )

    # 4. Save output
    if output_path:
        save_integrated_json(integrated_data, output_path)
        print(f"[Success] Saved {len(integrated_data['notes'])} notes to {output_path}")

    return integrated_data


def main():
    parser = argparse.ArgumentParser(description="Piano Finger Tracker & Visualizer Pipeline")
    parser.add_argument("--video", type=str, default=None, help="Path to input piano video (.mp4/.mov)")
    parser.add_argument("--midi", type=str, default=None, help="Path to input MIDI file (.mid)")
    parser.add_argument("--audio", type=str, default=None, help="Path to WAV audio file (optional)")
    parser.add_argument("--hands", type=str, default=None, help="Path to pre-extracted hands landmark JSON (optional)")
    parser.add_argument(
        "--quad",
        type=str,
        default="0.1,0.7,0.9,0.7,0.95,0.95,0.05,0.95",
        help="4 quad corners x0,y0,x1,y1,x2,y2,x3,y3 or JSON '[[x,y],...]'",
    )
    parser.add_argument("--output", type=str, default="web/data/ray_notes.json", help="Path to output JSON")
    parser.add_argument("--tolerance", type=float, default=0.05, help="Time matching tolerance (seconds)")
    parser.add_argument("--av-offset", type=float, default=0.0, help="A/V sync offset in seconds")
    parser.add_argument("--title", type=str, default="Piano Finger Tracking", help="Song/Recording title")

    args = parser.parse_args()

    quad = parse_quad_argument(args.quad)

    hands_data = None
    if args.hands and Path(args.hands).exists():
        with open(args.hands, "r", encoding="utf-8") as f:
            hands_data = json.load(f)

    result = run_pipeline(
        video_path=args.video,
        midi_path=args.midi,
        audio_path=args.audio,
        hands_data=hands_data,
        quad=quad,
        output_path=args.output,
        tolerance_sec=args.tolerance,
        av_offset_sec=args.av_offset,
        title=args.title,
    )

    print(f"Pipeline finished: {len(result['notes'])} notes processed.")


if __name__ == "__main__":
    main()
