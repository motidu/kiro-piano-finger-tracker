// Web/js/key_geometry.js
// Piano key geometry: 52 white keys, 36 black keys, MIDI 21–108.
// Camera is overhead; u in [0,1], v in [0,0.35] for keyboard strip.

export const MIN_NOTE = 21;
export const MAX_NOTE = 108;
export const WHITE_KEY_COUNT = 52;

// Pitch classes that are black keys (C#=1, D#=3, F#=6, G#=8, A#=10)
// Note: MIDI pitch class = note % 12
// C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11
const BLACK_PITCH_CLASSES = new Set([1, 3, 6, 8, 10]);

// Precompute white index for every MIDI note in [21, 108]
// whiteIndex(note) = number of white keys to the LEFT of this note
// For white keys: index of the white key itself (0-based)
// For black keys: index of the white key immediately to the left

const whiteIndexTable = new Array(108 - 21 + 1); // index by midi - 21
let wIdx = 0;
for (let m = 21; m <= 108; m++) {
  const pc = m % 12;
  if (!BLACK_PITCH_CLASSES.has(pc)) {
    whiteIndexTable[m - 21] = wIdx;
    wIdx++;
  } else {
    // Black key: whiteIndex is the index of the white key to its left
    whiteIndexTable[m - 21] = wIdx - 1;
  }
}

// Black key offsets in white-key widths (pitch class → offset)
// C#(1): -0.10, D#(3): +0.10, F#(6): -0.15, G#(8): 0.0, A#(10): +0.15
const blackOffsets = {
  1: -0.10,  // C#
  3: +0.10,  // D#
  6: -0.15,  // F#
  8: 0.0,    // G#
  10: +0.15  // A#
};

export function isBlack(note) {
  const pc = note % 12;
  return BLACK_PITCH_CLASSES.has(pc);
}

export function whiteIndex(note) {
  return whiteIndexTable[note - 21];
}

export function noteToU(note) {
  const wi = whiteIndex(note);
  if (!isBlack(note)) {
    // White key center: (whiteIndex + 0.5) / 52
    return (wi + 0.5) / WHITE_KEY_COUNT;
  }
  // Black key center: (whiteIndex + 1) / 52 + offset / 52
  const offset = blackOffsets[note % 12] || 0;
  return (wi + 1 + offset) / WHITE_KEY_COUNT;
}

export function keyWidthU(note) {
  if (!isBlack(note)) {
    return 1 / WHITE_KEY_COUNT;
  }
  return 0.58 / WHITE_KEY_COUNT;
}

// Precompute white key boundaries (u values for left edge of each white key)
// whiteKeyBoundaries[i] = u of the left edge of white key i
// white key i spans from i/52 to (i+1)/52
export function whiteKeyBoundaries() {
  const boundaries = [];
  for (let i = 0; i < WHITE_KEY_COUNT; i++) {
    boundaries.push(i / WHITE_KEY_COUNT);
  }
  boundaries.push(1.0); // right edge of last white key
  return boundaries;
}

// Precompute all black keys in range [21, 108]
export function allBlackKeys() {
  const keys = [];
  for (let m = 21; m <= 108; m++) {
    if (isBlack(m)) {
      keys.push(m);
    }
  }
  return keys;
}

// Precompute per-note geometry: { u, halfWidthU, isBlack }
const noteGeometryTable = new Array(108 - 21 + 1);
for (let m = 21; m <= 108; m++) {
  const u = noteToU(m);
  const wU = keyWidthU(m);
  const black = isBlack(m);
  noteGeometryTable[m - 21] = { u, halfWidthU: wU / 2, isBlack: black };
}

export function noteGeometry(midi) {
  return noteGeometryTable[midi - 21];
}
