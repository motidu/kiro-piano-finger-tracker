// web/js/audio_engine.js
// Web Audio API によるシンセサイザー音源

export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.activeVoices = new Map();
    this.masterGain = null;
    this.synthPanner = null;
    this.videoPanner = null;
    this.videoGain = null;
    this.videoSourceNode = null;
    this.videoElement = null;
    this.isVideoConnected = false;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();

      // Master Gain for Synth
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 1.0;

      // Synth Panner
      this.synthPanner = this.ctx.createStereoPanner();
      this.synthPanner.pan.value = 0.8; // Default right for MIDI

      // Connect chain: MasterGain -> SynthPanner -> Destination
      this.masterGain.connect(this.synthPanner);
      this.synthPanner.connect(this.ctx.destination);
    }
  }

  resume() {
    this.init();
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
  }

  playNote(pitch, duration = 0.5) {
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(this.midiToFreq(pitch), this.ctx.currentTime);

    // エンベロープ (アタック & ディケイ)
    gain.gain.setValueAtTime(0, this.ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.2, this.ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);

    osc.connect(gain);
    // Connect to master gain chain, not directly to destination
    gain.connect(this.masterGain);

    osc.start();
    osc.stop(this.ctx.currentTime + duration);
  }

  setPan(value) {
    if (!this.synthPanner) return;
    const clamped = Math.max(-1, Math.min(1, value));
    this.synthPanner.pan.value = clamped;
  }

  setVolume(value) {
    if (!this.masterGain) return;
    const clamped = Math.max(0.0, Math.min(1.5, value));
    this.masterGain.gain.value = clamped;
  }

  panVideo(videoElement, panValue = -0.8) {
    if (!this.ctx) this.init();

    // Guard against multiple connections
    if (this.isVideoConnected && this.videoElement === videoElement) {
      return;
    }

    try {
      // Disconnect previous if exists
      if (this.videoSourceNode) {
        this.videoSourceNode.disconnect();
        this.videoSourceNode = null;
      }

      const source = this.ctx.createMediaElementSource(videoElement);
      this.videoSourceNode = source;

      // Video Panner
      this.videoPanner = this.ctx.createStereoPanner();
      this.videoPanner.pan.value = Math.max(-1, Math.min(1, panValue));

      // Video Gain
      this.videoGain = this.ctx.createGain();
      this.videoGain.gain.value = 1.0;

      // Connect: Source -> VideoPanner -> VideoGain -> Destination
      source.connect(this.videoPanner);
      this.videoPanner.connect(this.videoGain);
      this.videoGain.connect(this.ctx.destination);

      this.videoElement = videoElement;
      this.isVideoConnected = true;
    } catch (e) {
      console.warn("Failed to connect video audio source (CORS/Policy):", e);
      this.isVideoConnected = false;
    }
  }

  setVideoPan(value) {
    if (!this.videoPanner) return;
    const clamped = Math.max(-1, Math.min(1, value));
    this.videoPanner.pan.value = clamped;
  }

  setVideoVolume(value) {
    if (!this.videoGain) return;
    const clamped = Math.max(0.0, Math.min(1.5, value));
    this.videoGain.gain.value = clamped;
  }
}
