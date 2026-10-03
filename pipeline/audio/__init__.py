"""Phase 3: Audio-to-MIDI Transcription Pipeline.

Extracts audio from video, detects piano notes, and outputs
normalized note events compatible with the HTML5 Canvas renderer.
"""

from pipeline.audio.midi_parser import parse_raw_events, NoteEvent

__all__ = ["parse_raw_events", "NoteEvent"]
