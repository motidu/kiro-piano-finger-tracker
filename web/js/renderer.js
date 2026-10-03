// web/js/renderer.js
// 60fps Canvas 落ち物ノート & 鍵盤描画

export class Renderer {
  constructor(canvas, perspective, notesData) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.perspective = perspective;
    this.notes = notesData || [];
    this.showCalibration = true;
    this.leadTimeSec = 2.0; // ノートが落ちてくる予兆時間（秒）
  }

  setNotes(notes) {
    this.notes = notes;
  }

  // MIDI番号 (21: A0 〜 108: C8) を 0.0〜1.0 に正規化
  midiToU(midi) {
    return Math.max(0, Math.min(1, (midi - 21) / (108 - 21)));
  }

  render(currentTime) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, w, h);

    // 1. 鍵盤ベースラインを描画
    this.drawKeyboard(w, h);

    // 2. 落ち物ノートの描画
    this.drawFallingNotes(currentTime, w, h);

    // 3. キャリブレーションピンの描画
    if (this.showCalibration) {
      this.drawCalibrationPins(w, h);
    }
  }

  drawKeyboard(w, h) {
    const ctx = this.ctx;
    const pFrontLeft = this.perspective.mapPoint(0, 0);
    const pFrontRight = this.perspective.mapPoint(1, 0);
    const pBackRight = this.perspective.mapPoint(1, 0.35);
    const pBackLeft = this.perspective.mapPoint(0, 0.35);

    // 鍵盤エリアの背景
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.beginPath();
    ctx.moveTo(pFrontLeft.x * w, pFrontLeft.y * h);
    ctx.lineTo(pFrontRight.x * w, pFrontRight.y * h);
    ctx.lineTo(pBackRight.x * w, pBackRight.y * h);
    ctx.lineTo(pBackLeft.x * w, pBackLeft.y * h);
    ctx.closePath();
    ctx.fill();

    // 鍵盤の外枠
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // 白鍵の縦ライン（簡易88鍵ガイド線）
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;
    for (let m = 21; m <= 108; m++) {
      const u = this.midiToU(m);
      const front = this.perspective.mapPoint(u, 0);
      const back = this.perspective.mapPoint(u, 0.35);
      ctx.beginPath();
      ctx.moveTo(front.x * w, front.y * h);
      ctx.lineTo(back.x * w, back.y * h);
      ctx.stroke();
    }
  }

  drawFallingNotes(currentTime, w, h) {
    const ctx = this.ctx;

    // 現在時刻の前後に存在するノートを抽出
    const visibleNotes = this.notes.filter(n => {
      return n.end >= currentTime && n.start <= currentTime + this.leadTimeSec;
    });

    visibleNotes.forEach(n => {
      const isLeft = n.hand === "L";
      const color = isLeft ? "#3b82f6" : "#ec4899";
      const u = this.midiToU(n.note);

      // 奥行き v の計算 (0: 鍵盤上 〜 1: 最上部)
      // ノートの先端（着地予定地点）
      const vFront = Math.max(0, 0.35 + ((n.start - currentTime) / this.leadTimeSec) * 0.65);
      // ノートの末尾
      const vBack = Math.min(1.0, 0.35 + ((n.end - currentTime) / this.leadTimeSec) * 0.65);

      const pFront = this.perspective.mapPoint(u, vFront);
      const pBack = this.perspective.mapPoint(u, vBack);

      // 落ち物バーの描画
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(4, 12 * (1 - vFront * 0.5));
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(pFront.x * w, pFront.y * h);
      ctx.lineTo(pBack.x * w, pBack.y * h);
      ctx.stroke();

      // 現在まさに打鍵中の場合：鍵盤上にヒットエフェクト & 指番号バッジを表示
      if (currentTime >= n.start && currentTime <= n.end) {
        const hitPoint = this.perspective.mapPoint(u, 0.15);

        // 打鍵発光エフェクト
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(hitPoint.x * w, hitPoint.y * h, 14, 0, Math.PI * 2);
        ctx.fill();

        // 指番号 (1〜5)
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(n.finger ? String(n.finger) : "", hitPoint.x * w, hitPoint.y * h);
      }
    });
  }

  drawCalibrationPins(w, h) {
    const ctx = this.ctx;
    const pts = this.perspective.points;

    Object.entries(pts).forEach(([key, pt]) => {
      const px = pt.x * w;
      const py = pt.y * h;

      ctx.fillStyle = "#10b981";
      ctx.beginPath();
      ctx.arc(px, py, 8, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = "#ffffff";
      ctx.font = "12px sans-serif";
      ctx.fillText(key, px + 12, py + 4);
    });
  }
}
