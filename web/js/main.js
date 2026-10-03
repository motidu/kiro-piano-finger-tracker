// web/js/main.js
import { PerspectiveMapper } from "./perspective.js";
import { AudioEngine } from "./audio_engine.js";
import { Renderer } from "./renderer.js";

document.addEventListener("DOMContentLoaded", async () => {
  const canvas = document.getElementById("viewer-canvas");
  const playBtn = document.getElementById("btn-play");
  const calibBtn = document.getElementById("btn-calib");
  const timeSlider = document.getElementById("time-slider");
  const timeLabel = document.getElementById("time-label");
  const statusLabel = document.getElementById("status-text");

  // キャンバスのリサイズ対応
  const resizeCanvas = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  // サブシステムの初期化
  const perspective = new PerspectiveMapper();
  const audioEngine = new AudioEngine();
  let notesData = [];

  // JSON ノートデータの読み込み
  try {
    const res = await fetch("./data/ray_notes.json");
    if (!res.ok) throw new Error("JSON fetch failed");
    const json = await res.json();
    notesData = json.notes || [];
    statusLabel.textContent = `読込完了: ${notesData.length} ノート`;
  } catch (err) {
    statusLabel.textContent = "ノートデータ読込エラー";
    console.error(err);
  }

  const renderer = new Renderer(canvas, perspective, notesData);

  // 再生タイムライン管理
  let isPlaying = false;
  let currentTime = 0;
  let lastTimestamp = 0;
  let playedNoteIndices = new Set();
  const duration = 12.0;

  // requestAnimationFrame ループ
  const animate = (timestamp) => {
    if (!lastTimestamp) lastTimestamp = timestamp;
    const dt = (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;

    if (isPlaying) {
      currentTime += dt;
      if (currentTime > duration) {
        currentTime = 0;
        playedNoteIndices.clear();
      }
      timeSlider.value = currentTime;
      timeLabel.textContent = `${currentTime.toFixed(1)}s / ${duration.toFixed(1)}s`;

      // Web Audio での音再生
      notesData.forEach((n, idx) => {
        if (!playedNoteIndices.has(idx) && currentTime >= n.start && currentTime <= n.end) {
          audioEngine.playNote(n.note, n.end - n.start);
          playedNoteIndices.add(idx);
        }
      });
    }

    renderer.render(currentTime);
    requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);

  // UI コントロールのイベント設定
  playBtn.addEventListener("click", () => {
    audioEngine.resume();
    isPlaying = !isPlaying;
    playBtn.textContent = isPlaying ? "⏸ 一時停止" : "▶ 再生";
    playBtn.classList.toggle("active", isPlaying);
  });

  timeSlider.addEventListener("input", (e) => {
    currentTime = parseFloat(e.target.value);
    playedNoteIndices.clear();
    timeLabel.textContent = `${currentTime.toFixed(1)}s / ${duration.toFixed(1)}s`;
  });

  calibBtn.addEventListener("click", () => {
    renderer.showCalibration = !renderer.showCalibration;
    calibBtn.classList.toggle("active", renderer.showCalibration);
  });

  // キャリブレーションピンのドラッグ操作
  let activePin = null;

  canvas.addEventListener("mousedown", (e) => {
    if (!renderer.showCalibration) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / canvas.width;
    const my = (e.clientY - rect.top) / canvas.height;

    // 最寄りのピンを検索
    for (const [key, pt] of Object.entries(perspective.points)) {
      const dist = Math.hypot(pt.x - mx, pt.y - my);
      if (dist < 0.05) {
        activePin = key;
        break;
      }
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (!activePin) return;
    const rect = canvas.getBoundingClientRect();
    const mx = Math.max(0, Math.min(1, (e.clientX - rect.left) / canvas.width));
    const my = Math.max(0, Math.min(1, (e.clientY - rect.top) / canvas.height));
    perspective.setPoint(activePin, mx, my);
  });

  window.addEventListener("mouseup", () => {
    activePin = null;
  });
});
