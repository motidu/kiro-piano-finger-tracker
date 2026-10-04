// web/js/midi_parser.js
// Zero-dependency Standard MIDI File (SMF) parser for browser execution

export function parseMidiArrayBuffer(arrayBuffer) {
  const bytes = new Uint8Array(arrayBuffer);
  let pos = 0;

  function readStr(n) {
    let s = "";
    for (let i = 0; i < n; i++) s += String.fromCharCode(bytes[pos++]);
    return s;
  }

  function read16() {
    return (bytes[pos++] << 8) | bytes[pos++];
  }

  function read32() {
    return (bytes[pos++] << 24) | (bytes[pos++] << 16) | (bytes[pos++] << 8) | bytes[pos++];
  }

  function readVarLen() {
    let value = 0;
    let byte;
    do {
      byte = bytes[pos++];
      value = (value << 7) | (byte & 0x7f);
    } while (byte & 0x80);
    return value;
  }

  // Parse MThd header
  const magic = readStr(4);
  if (magic !== "MThd") {
    throw new Error("Invalid MIDI file: missing MThd header");
  }
  const headerLen = read32();
  const format = read16();
  const numTracks = read16();
  const ticksPerQuarter = read16();

  // Skip any remaining header bytes
  pos += headerLen - 6;

  const notes = [];
  let currentTempo = 500000; // microseconds per quarter note (default 120 BPM)

  function ticksToSeconds(ticks) {
    return (ticks / ticksPerQuarter) * (currentTempo / 1000000);
  }

  // Parse each MTrk
  for (let track = 0; track < numTracks; track++) {
    if (pos >= bytes.length) break;

    const chunkId = readStr(4);
    if (chunkId !== "MTrk") {
      const chunkLen = read32();
      pos += chunkLen;
      continue;
    }

    const trackLen = read32();
    const trackEnd = pos + trackLen;

    let runningStatus = 0;
    let absTicks = 0;
    const activeNotes = new Map(); // note -> { startTicks, velocity }

    while (pos < trackEnd && pos < bytes.length) {
      const delta = readVarLen();
      absTicks += delta;

      if (pos >= trackEnd) break;

      let status = bytes[pos];

      if (status < 0x80) {
        status = runningStatus;
      } else {
        runningStatus = status;
        pos++;
      }

      if (status === 0xff) {
        // Meta event
        const metaType = bytes[pos++];
        const metaLen = readVarLen();
        if (metaType === 0x51 && metaLen === 3) {
          // Set tempo
          currentTempo = (bytes[pos] << 16) | (bytes[pos + 1] << 8) | bytes[pos + 2];
        }
        pos += metaLen;
      } else if (status >= 0x80 && status <= 0x8f) {
        // Note Off
        const note = bytes[pos++];
        const vel = bytes[pos++];
        if (activeNotes.has(note)) {
          const { startTicks, velocity } = activeNotes.get(note);
          activeNotes.delete(note);
          const startSec = ticksToSeconds(startTicks);
          const endSec = Math.max(ticksToSeconds(absTicks), startSec + 0.05);
          notes.push({
            note: note,
            start: round4(startSec),
            end: round4(endSec),
            velocity: round2(velocity),
            finger: 0,
            hand: note < 60 ? "L" : "R",
          });
        }
      } else if (status >= 0x90 && status <= 0x9f) {
        // Note On
        const note = bytes[pos++];
        const velocity = bytes[pos++];
        if (velocity > 0) {
          if (note >= 21 && note <= 108) {
            activeNotes.set(note, { startTicks: absTicks, velocity });
          }
        } else {
          // Velocity 0 is note off
          if (activeNotes.has(note)) {
            const { startTicks, velocity: origVel } = activeNotes.get(note);
            activeNotes.delete(note);
            const startSec = ticksToSeconds(startTicks);
            const endSec = Math.max(ticksToSeconds(absTicks), startSec + 0.05);
            notes.push({
              note: note,
              start: round4(startSec),
              end: round4(endSec),
              velocity: round2(origVel),
              finger: 0,
              hand: note < 60 ? "L" : "R",
            });
          }
        }
      } else if (status >= 0xc0 && status <= 0xdf) {
        // Program change or channel pressure (1 data byte)
        pos += 1;
      } else if (status >= 0x80 && status <= 0xef) {
        // 2 data bytes
        pos += 2;
      } else if (status >= 0xf0) {
        // Sysex
        const len = readVarLen();
        pos += len;
      }
    }

    // Flush any still open notes
    for (const [note, { startTicks, velocity }] of activeNotes.entries()) {
      const startSec = ticksToSeconds(startTicks);
      notes.push({
        note: note,
        start: round4(startSec),
        end: round4(startSec + 0.25),
        velocity: round2(velocity),
        finger: 0,
        hand: note < 60 ? "L" : "R",
      });
    }

    pos = trackEnd;
  }

  function round4(v) { return Math.round(v * 10000) / 10000; }
  function round2(v) { return Math.round(v * 100) / 100; }

  notes.sort((a, b) => a.start - b.start);
  const duration = notes.length > 0 ? Math.max(...notes.map(n => n.end)) : 12.0;

  return { notes, duration: round4(duration) };
}
