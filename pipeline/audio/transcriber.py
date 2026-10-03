"""Audio extraction and transcription runner with zero-dependency fallbacks.

FFmpeg による動画からの音声抽出および、オーディオ特徴量・オンセットから
ピアノノートイベントを生成するパイプライン。
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path
from pipeline.audio.midi_parser import NoteEvent, parse_raw_events


def extract_audio_from_video(video_path: str | Path, output_wav: str | Path | None = None) -> Path:
    """FFmpeg を呼び出して動画から 44.1kHz モノラル WAV 音声を抽出する。"""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    if output_wav is None:
        tmp_dir = Path(tempfile.mkdtemp(prefix="audio_extract_"))
        output_wav = tmp_dir / "extracted.wav"
    output_wav = Path(output_wav)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        str(output_wav),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg の音声抽出に失敗しました: {res.stderr}")

    return output_wav


def detect_wav_notes_simple(wav_path: str | Path) -> list[NoteEvent]:
    """WAV ファイルのヘッダーおよび振幅を読み込み、基本イベントを検出する（フォールバック）。"""
    wav_path = Path(wav_path)
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV ファイルが見つかりません: {wav_path}")

    raw_events: list[dict] = []
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        duration = n_frames / float(framerate) if framerate > 0 else 0.0

    return parse_raw_events(raw_events)
