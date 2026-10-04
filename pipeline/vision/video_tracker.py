"""Video-based hand landmark extraction using MediaPipe HandLandmarker.

Extracts 21 hand landmarks per frame, identifies 5 fingertips,
computes normalized timestamps, and outputs hand data compatible
with FingerKeyMapper.map_fingers_to_keys().
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Fingertip landmark indices in MediaPipe 21-point hand model
FINGERTIP_INDICES: Dict[int, int] = {
    1: 4,   # Thumb
    2: 8,   # Index
    3: 12,  # Middle
    4: 16,  # Ring
    5: 20,  # Pinky
}

FINGER_NAMES: Dict[int, str] = {
    1: "Thumb",
    2: "Index",
    3: "Middle",
    4: "Ring",
    5: "Pinky",
}


def extract_hands_from_video(
    video_path: str | Path,
    model_path: str | Path = "models/hand_landmarker.task",
    max_hands: int = 2,
    min_detection_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
    mirror_handedness: bool = False,
) -> List[Dict[str, Any]]:
    """Extract hand landmarks from a video file using MediaPipe HandLandmarker.

    Args:
        video_path: Path to the input video file.
        model_path: Path to the .task model file for HandLandmarker.
        max_hands: Maximum number of hands to detect per frame.
        min_detection_confidence: Minimum confidence for hand detection.
        min_tracking_confidence: Minimum confidence for hand tracking.
        mirror_handedness: If True, swap hand_id 0<->1 for non-selfie footage.

    Returns:
        List of hand dicts, each containing:
            - timestamp: float (seconds)
            - hand_id: int (0=left, 1=right)
            - fingers: list of {x, y, finger_id} normalized [0,1]
            - landmarks: list of 21 (x,y) normalized points
    """
    video_path = Path(video_path)
    model_path = Path(model_path)

    # Check if cv2 and mediapipe are available in the current environment
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
    except ImportError as e:
        # Check if the piano_transcription_mixed .venv python is available with mediapipe
        venv_py = Path(r"G:\Dev\piano_transcription_mixed\.venv\Scripts\python.exe")
        if venv_py.exists():
            return _extract_hands_via_subshell(video_path, model_path, venv_py, mirror_handedness)
        print(f"[Warning] cv2/mediapipe not available in current Python ({e}).", file=sys.stderr)
        return []

    if not model_path.exists():
        # Fallback to alternative model path in piano_transcription_mixed
        alt_model = Path(r"G:\Dev\piano_transcription_mixed\hand_landmarker.task")
        if alt_model.exists():
            model_path = alt_model
        else:
            print(f"[Warning] MediaPipe model file not found: {model_path}", file=sys.stderr)
            return []

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path.resolve())),
        running_mode=RunningMode.VIDEO,
        num_hands=max_hands,
        min_hand_detection_confidence=min_detection_confidence,
        min_hand_presence_confidence=min_tracking_confidence,
    )

    try:
        landmarker = HandLandmarker.create_from_options(options)
    except Exception as e:
        print(f"[Warning] Failed to initialize HandLandmarker ({e}).", file=sys.stderr)
        return []

    results: List[Dict[str, Any]] = []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[Error] Cannot open video file: {video_path}", file=sys.stderr)
        landmarker.close()
        return results

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        timestamp_ms = int(frame_idx * 1000.0 / fps)

        try:
            detection = landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception:
            try:
                detection = landmarker.detect(mp_image, timestamp_ms)
            except Exception:
                frame_idx += 1
                continue

        if detection and detection.hand_landmarks:
            timestamp_sec = round(frame_idx / fps, 4)

            for hand_idx, landmarks in enumerate(detection.hand_landmarks):
                # 0 = Left, 1 = Right
                hand_id = 0
                if detection.handedness and hand_idx < len(detection.handedness):
                    label = detection.handedness[hand_idx][0].display_name
                    if label.lower() == "right":
                        hand_id = 1

                # Apply mirror correction if requested
                if mirror_handedness:
                    hand_id = 1 - hand_id

                pts = [(lm.x, lm.y) for lm in landmarks]

                fingers = []
                for finger_id, landmark_idx in FINGERTIP_INDICES.items():
                    if landmark_idx < len(pts):
                        x, y = pts[landmark_idx]
                        fingers.append({
                            "x": round(float(x), 4),
                            "y": round(float(y), 4),
                            "finger_id": finger_id,
                        })

                results.append({
                    "timestamp": timestamp_sec,
                    "hand_id": hand_id,
                    "fingers": fingers,
                    "landmarks": [(round(p[0], 4), round(p[1], 4)) for p in pts],
                })

        frame_idx += 1

    cap.release()
    landmarker.close()

    results.sort(key=lambda h: h["timestamp"])
    return results


def _extract_hands_via_subshell(
    video_path: Path,
    model_path: Path,
    venv_python: Path,
    mirror_handedness: bool = False,
) -> List[Dict[str, Any]]:
    """Delegate extraction to the .venv Python where cv2 and mediapipe are installed."""
    import json
    import subprocess
    import tempfile

    tmp_out = Path(tempfile.mktemp(suffix=".json"))
    script_content = f"""
import json, sys
from pipeline.vision.video_tracker import extract_hands_from_video

results = extract_hands_from_video(r"{video_path}", r"{model_path}", mirror_handedness={mirror_handedness})
with open(r"{tmp_out}", "w", encoding="utf-8") as f:
    json.dump(results, f)
"""
    cmd = [str(venv_python), "-c", script_content]
    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=300)
        if res.returncode == 0 and tmp_out.exists():
            with open(tmp_out, "r", encoding="utf-8") as f:
                data = json.load(f)
            tmp_out.unlink(missing_ok=True)
            return data
    except Exception as e:
        print(f"[Warning] Subshell video tracking failed ({e}).", file=sys.stderr)
    finally:
        tmp_out.unlink(missing_ok=True)
    return []
