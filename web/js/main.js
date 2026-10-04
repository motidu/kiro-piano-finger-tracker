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

  const inputLoadJson = document.getElementById("input-load-json");
  const inputLoadVideo = document.getElementById("input-load-video");
  const btnLoadJson = document.getElementById("btn-load-json");
  const btnLoadVideo = document.getElementById("btn-load-video");
  const loadedFileBadge = document.getElementById("loaded-file-badge");
  const dropOverlay = document.getElementById("drop-overlay");

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

  // JSON ノートデータの初期読み込み
  try {
    const res = await fetch("./data/ray_notes.json");
    if (!res.ok) throw new Error("JSON fetch failed");
    const json = await res.json();
    notesData = json.notes || [];
    statusLabel.textContent = `読込完了: ${notesData.length} ノート`;
  } catch (err) {
    statusLabel.textContent = "ノートデータ読込待機中";
    console.warn("Default notes JSON not loaded:", err);
  }

  const renderer = new Renderer(canvas, perspective, notesData);

  // 再生タイムライン管理
  let isPlaying = false;
  let currentTime = 0;
  let lastTimestamp = 0;
  let playedNoteIndices = new Set();
  let duration = 12.0;
  let videoEl = null;

  // 再生/一時停止の統一トグル
  const togglePlay = () => {
    audioEngine.resume();
    isPlaying = !isPlaying;
    playBtn.textContent = isPlaying ? "⏸ 一時停止" : "▶ 再生";
    playBtn.classList.toggle("active", isPlaying);

    if (videoEl) {
      if (isPlaying) {
        videoEl.play().catch(e => console.warn("Video play interrupted:", e));
      } else {
        videoEl.pause();
      }
    }
  };

  // requestAnimationFrame ループ
  const animate = (timestamp) => {
    if (!lastTimestamp) lastTimestamp = timestamp;
    const dt = (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;

    if (isPlaying) {
      if (videoEl && !videoEl.paused) {
        currentTime = videoEl.currentTime;
      } else {
        currentTime += dt;
      }

      if (currentTime > duration) {
        currentTime = 0;
        playedNoteIndices.clear();
        if (videoEl) videoEl.currentTime = 0;
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
  playBtn.addEventListener("click", togglePlay);

  // スペースキーでの再生/一時停止ショートカット
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && e.target.tagName !== "INPUT") {
      e.preventDefault();
      togglePlay();
    }
  });

  timeSlider.addEventListener("input", (e) => {
    currentTime = parseFloat(e.target.value);
    playedNoteIndices.clear();
    timeLabel.textContent = `${currentTime.toFixed(1)}s / ${duration.toFixed(1)}s`;
    if (videoEl) {
      videoEl.currentTime = currentTime;
    }
  });

  calibBtn.addEventListener("click", () => {
    renderer.showCalibration = !renderer.showCalibration;
    calibBtn.classList.toggle("active", renderer.showCalibration);
    if (!renderer.showCalibration) {
      canvas.style.cursor = "default";
    }
  });

  // キャリブレーションピンのドラッグ操作 (Modern Pointer Events)
  let activePin = null;

  canvas.addEventListener("pointerdown", (e) => {
    if (!renderer.showCalibration) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;

    for (const [key, pt] of Object.entries(perspective.points)) {
      const targetX = pt.x * rect.width;
      const targetY = pt.y * rect.height;
      const dist = Math.hypot(px - targetX, py - targetY);

      if (dist <= 25) {
        activePin = key;
        canvas.setPointerCapture(e.pointerId);
        canvas.style.cursor = "grabbing";
        break;
      }
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!renderer.showCalibration) {
      canvas.style.cursor = "default";
      return;
    }

    const rect = canvas.getBoundingClientRect();

    if (!activePin) {
      // ピンホバー判定（視覚的カーソルフィードバック）
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      let isHovering = false;

      for (const [key, pt] of Object.entries(perspective.points)) {
        const targetX = pt.x * rect.width;
        const targetY = pt.y * rect.height;
        const dist = Math.hypot(px - targetX, py - targetY);
        if (dist <= 25) {
          isHovering = true;
          break;
        }
      }
      canvas.style.cursor = isHovering ? "grab" : "default";
      return;
    }

    // ピンのドラッグ移動
    const mx = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const my = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    perspective.setPoint(activePin, mx, my);
  });

  canvas.addEventListener("pointerup", (e) => {
    if (activePin) {
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch (_) {}
      activePin = null;
      canvas.style.cursor = "grab";
    }
  });

  canvas.addEventListener("pointercancel", (e) => {
    if (activePin) {
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch (_) {}
      activePin = null;
      canvas.style.cursor = "default";
    }
  });

  // 動的 JSON ファイル読み込み処理
  function handleJsonFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target.result);
        if (!json.notes || !Array.isArray(json.notes)) {
          statusLabel.textContent = "JSON形式エラー: notes配列がありません";
          return;
        }
        notesData = json.notes;
        renderer.notes = notesData;

        // 再生時間の更新
        const maxEnd = notesData.length > 0 ? Math.max(...notesData.map(n => n.end)) : 12.0;
        duration = json.meta?.duration_sec || maxEnd || 12.0;
        timeSlider.max = duration;
        currentTime = 0;
        playedNoteIndices.clear();
        timeSlider.value = 0;
        timeLabel.textContent = `0.0s / ${duration.toFixed(1)}s`;
        statusLabel.textContent = `読込完了: ${notesData.length} ノート`;
        loadedFileBadge.textContent = file.name;

        if (videoEl) videoEl.currentTime = 0;
      } catch (err) {
        statusLabel.textContent = "JSON解析エラー";
        console.error(err);
      }
    };
    reader.readAsText(file);
  }

  // 動的 動画ファイル読み込み処理
  function handleVideoFile(file) {
    const url = URL.createObjectURL(file);
    if (!videoEl) {
      videoEl = document.createElement("video");
      videoEl.id = "bg-video";
      videoEl.style.position = "absolute";
      videoEl.style.top = "0";
      videoEl.style.left = "0";
      videoEl.style.width = "100%";
      videoEl.style.height = "100%";
      videoEl.style.objectFit = "cover";
      videoEl.style.zIndex = "0";
      videoEl.style.opacity = "0.45";
      videoEl.playsInline = true;
      document.getElementById("canvas-container").prepend(videoEl);
    }
    videoEl.src = url;
    loadedFileBadge.textContent = file.name;
    statusLabel.textContent = `動画セット: ${file.name}`;

    videoEl.addEventListener("loadedmetadata", () => {
      if (videoEl.duration && !isNaN(videoEl.duration)) {
        duration = videoEl.duration;
        timeSlider.max = duration;
        timeLabel.textContent = `${currentTime.toFixed(1)}s / ${duration.toFixed(1)}s`;
      }
    });

    if (isPlaying) {
      videoEl.play().catch(e => console.warn("Autoplay blocked:", e));
    }
  }

  // ボタンクリックハンドラー
  btnLoadJson.addEventListener("click", () => {
    inputLoadJson.click();
  });

  btnLoadVideo.addEventListener("click", () => {
    inputLoadVideo.click();
  });

  inputLoadJson.addEventListener("change", (e) => {
    if (e.target.files[0]) handleJsonFile(e.target.files[0]);
    e.target.value = "";
  });

  inputLoadVideo.addEventListener("change", (e) => {
    if (e.target.files[0]) handleVideoFile(e.target.files[0]);
    e.target.value = "";
  });

  // ドラッグ＆ドロップハンドラー
  window.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropOverlay.classList.add("active");
  });

  window.addEventListener("dragleave", (e) => {
    if (e.clientX <= 0 || e.clientY <= 0 || e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
      dropOverlay.classList.remove("active");
    }
  });

  window.addEventListener("drop", (e) => {
    e.preventDefault();
    dropOverlay.classList.remove("active");
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      for (const file of files) {
        if (file.name.endsWith(".json")) {
          handleJsonFile(file);
        } else if (file.type.startsWith("video/") || file.name.match(/\.(mp4|webm|mov|mkv)$/i)) {
          handleVideoFile(file);
        }
      }
    }
  });
});
