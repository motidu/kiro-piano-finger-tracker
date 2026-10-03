"""End-to-end pipeline orchestrator for piano finger tracking.

Combines audio transcription (AudioTranscriber), vision key-finger mapping
(process_video_frames / FingerKeyMapper), and temporal integration
(build_ray_notes / save_integrated_json).
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

from pipeline.audio.transcriber import (
    extract_audio_from_video,
    detect_wav_notes_simple,
    parse_raw_events,
)
from pipeline.vision.finger_mapper import FingerKeyMapper
from pipeline.vision.main_vision import process_video_frames
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
    audio_path: str | Path | None = None,
    hands_data: List[Dict[str, Any]] | None = None,
    audio_events: List[Dict[str, Any]] | None = None,
    quad: Tuple[Tuple[float, float], ...] = DEFAULT_QUAD,
    output_path: str | Path = "web/data/ray_notes.json",
    tolerance_sec: float = 0.05,
    title: str = "Piano Finger Tracking",
) -> Dict[str, Any]:
    """Execute end-to-end integration pipeline.

    Args:
        video_path: Input video file path.
        audio_path: Optional separate WAV file path.
        hands_data: Pre-extracted hand landmark data (list of hands).
        audio_events: Pre-extracted audio NoteEvent list.
        quad: 4 corner coordinates (TL, TR, BR, BL).
        output_path: Target destination path for ray_notes.json.
        tolerance_sec: Synchronization tolerance in seconds (default 50ms).
        title: Meta title for the dataset.

    Returns:
        Resulting ray_notes dictionary.
    """
    # 1. Process Audio
    if audio_events is None:
        if audio_path is not None:
            audio_wav = Path(audio_path)
            audio_events = detect_wav_notes_simple(audio_wav)
        elif video_path is not None and Path(video_path).exists():
            try:
                audio_wav = extract_audio_from_video(video_path)
                audio_events = detect_wav_notes_simple(audio_wav)
            except Exception as e:
                print(f"[Warning] Audio extraction from video failed ({e}). Using empty audio events.", file=sys.stderr)
                audio_events = []
        else:
            audio_events = []

    # 2. Process Vision
    if hands_data is None:
        hands_data = []

    vision_mapper = FingerKeyMapper(quad)
    vision_events = vision_mapper.map_fingers_to_keys(hands_data, quad)

    # 3. Integrate & Merge
    integrated_data = build_ray_notes(
        audio_events=audio_events,
        vision_events=vision_events,
        tolerance_sec=tolerance_sec,
        title=title,
    )

    # 4. Save output
    if output_path:
        save_integrated_json(integrated_data, output_path)

    return integrated_data


def main():
    parser = argparse.ArgumentParser(description="Piano Finger Tracker & Visualizer Pipeline")
    parser.add_argument("--video", type=str, default=None, help="Path to input piano video")
    parser.add_argument("--audio", type=str, default=None, help="Path to WAV audio file")
    parser.add_argument("--hands", type=str, default=None, help="Path to hands landmark JSON")
    parser.add_argument(
        "--quad",
        type=str,
        default="0.1,0.7,0.9,0.7,0.95,0.95,0.05,0.95",
        help="4 quad corners x0,y0,x1,y1,x2,y2,x3,y3 or JSON '[[x,y],...]'",
    )
    parser.add_argument("--output", type=str, default="web/data/ray_notes.json", help="Path to output JSON")
    parser.add_argument("--tolerance", type=float, default=0.05, help="Time matching tolerance (seconds)")
    parser.add_argument("--title", type=str, default="Piano Finger Tracking", help="Song/Recording title")

    args = parser.parse_args()

    quad = parse_quad_argument(args.quad)

    hands_data = None
    if args.hands and Path(args.hands).exists():
        with open(args.hands, "r", encoding="utf-8") as f:
            hands_data = json.load(f)

    result = run_pipeline(
        video_path=args.video,
        audio_path=args.audio,
        hands_data=hands_data,
        quad=quad,
        output_path=args.output,
        tolerance_sec=args.tolerance,
        title=args.title,
    )

    print(f"Pipeline finished: {len(result['notes'])} notes processed into {args.output}")


if __name__ == "__main__":
    main()
