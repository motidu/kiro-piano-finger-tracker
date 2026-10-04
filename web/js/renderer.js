// web/js/renderer.js
// 60fps Canvas 落ち物ノート & 鍵盤描画

import { noteToU, keyWidthU, isBlack, whiteKeyBoundaries, allBlackKeys, WHITE_KEY_COUNT, noteGeometry } from "./key_geometry.js";

export class Renderer {
  constructor(canvas, perspective, notesData) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.perspective = perspective;
    this.notes = notesData || [];
    this.showCalibration = true;
    this.leadTimeSec = 2.0; // ノートが落ちてくる予兆時間（秒）

    // Precompute keyboard geometry
    this._whiteBoundaries = whiteKeyBoundaries();
    this._blackKeys = allBlackKeys();
    this._whiteKeyCount = WHITE_KEY_COUNT;
  }

  setNotes(notes) {
    this.notes = notes;
  }

  // MIDI番号 (21: A0 〜 108: C8) を 0.0〜1.0 に正規化
  midiToU(midi) {
    return noteToU(midi);
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

    // 白鍵の描画：52 white keys as quads
    const boundaries = this._whiteBoundaries;
    ctx.fillStyle = "rgba(240, 240, 245, 0.92)";
    for (let i = 0; i < boundaries.length - 1; i++) {
      const uLeft = boundaries[i];
      const uRight = boundaries[i + 1];

      const fl = this.perspective.mapPoint(uLeft, 0);
      const fr = this.perspective.mapPoint(uRight, 0);
      const br = this.perspective.mapPoint(uRight, 0.35);
      const bl = this.perspective.mapPoint(uLeft, 0.35);

      ctx.beginPath();
      ctx.moveTo(fl.x * w, fl.y * h);
      ctx.lineTo(fr.x * w, fr.y * h);
      ctx.lineTo(br.x * w, br.y * h);
      ctx.lineTo(bl.x * w, bl.y * h);
      ctx.closePath();
      ctx.fill();
    }

    // Thin separators between white keys
    ctx.strokeStyle = "rgba(180, 180, 190, 0.6)";
    ctx.lineWidth = 1;
    for (let i = 1; i < boundaries.length - 1; i++) {
      const u = boundaries[i];
      const front = this.perspective.mapPoint(u, 0);
      const back = this.perspective.mapPoint(u, 0.35);
      ctx.beginPath();
      ctx.moveTo(front.x * w, front.y * h);
      ctx.lineTo(back.x * w, back.y * h);
      ctx.stroke();
    }

    // Black keys: draw as dark quads covering back 60% of key depth (v from 0.14 to 0.35)
    ctx.fillStyle = "rgba(20, 20, 30, 0.95)";
    for (const midi of this._blackKeys) {
      const geom = noteGeometry(midi);
      const uCenter = geom.u;
      const halfW = geom.halfWidthU;
      const uLeft = uCenter - halfW;
      const uRight = uCenter + halfW;

      // v range for black keys: 0.14 to 0.35 (back 60% of 0..0.35 strip)
      const vFront = 0.14;
      const vBack = 0.35;

      const fl = this.perspective.mapPoint(uLeft, vFront);
      const fr = this.perspective.mapPoint(uRight, vFront);
      const br = this.perspective.mapPoint(uRight, vBack);
      const bl = this.perspective.mapPoint(uLeft, vBack);

      ctx.beginPath();
      ctx.moveTo(fl.x * w, fl.y * h);
      ctx.lineTo(fr.x * w, fr.y * h);
      ctx.lineTo(br.x * w, br.y * h);
      ctx.lineTo(bl.x * w, bl.y * h);
      ctx.closePath();
      ctx.fill();
    }

    // Keyboard outer frame
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pFrontLeft.x * w, pFrontLeft.y * h);
    ctx.lineTo(pFrontRight.x * w, pFrontRight.y * h);
    ctx.lineTo(pBackRight.x * w, pBackRight.y * h);
    ctx.lineTo(pBackLeft.x * w, pBackLeft.y * h);
    ctx.closePath();
    ctx.stroke();
  }

  drawFallingNotes(currentTime, w, h) {
    const ctx = this.ctx;

    // 現在時刻の前後に存在するノートを抽出
    const visibleNotes = this.notes.filter(n => {
      return n.end >= currentTime && n.start <= currentTime + this.leadTimeSec;
    });

    visibleNotes.forEach(n => {
      const isLeft = n.hand === "L" || n.hand === "left" || n.hand === 0 || String(n.hand).toLowerCase() === "left";
      const color = isLeft ? "#3b82f6" : "#ec4899";

      const geom = noteGeometry(n.note);
      const uCenter = geom.u;
      const halfW = geom.halfWidthU;
      const uLeft = uCenter - halfW;
      const uRight = uCenter + halfW;

      // 奥行き v の計算 (0: 鍵盤上 〜 1: 最上部)
      // ノートの先端（着地予定地点）
      const vFront = Math.max(0, 0.35 + ((n.start - currentTime) / this.leadTimeSec) * 0.65);
      // ノートの末尾
      const vBack = Math.min(1.0, 0.35 + ((n.end - currentTime) / this.leadTimeSec) * 0.65);

      // Draw falling note bar as a quad (left edge and right edge lines)
      const pFrontL = this.perspective.mapPoint(uLeft, vFront);
      const pFrontR = this.perspective.mapPoint(uRight, vFront);
      const pBackL = this.perspective.mapPoint(uLeft, vBack);
      const pBackR = this.perspective.mapPoint(uRight, vBack);

      // Bar fill
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.7;
      ctx.beginPath();
      ctx.moveTo(pFrontL.x * w, pFrontL.y * h);
      ctx.lineTo(pFrontR.x * w, pFrontR.y * h);
      ctx.lineTo(pBackR.x * w, pBackR.y * h);
      ctx.lineTo(pBackL.x * w, pBackL.y * h);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // Outline: black keys get slightly darker outline, white keys use hand color
      const outlineColor = geom.isBlack ? "#1a1a2e" : color;
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = Math.max(2, 6 * (1 - vFront * 0.5));
      ctx.beginPath();
      ctx.moveTo(pFrontL.x * w, pFrontL.y * h);
      ctx.lineTo(pFrontR.x * w, pFrontR.y * h);
      ctx.lineTo(pBackR.x * w, pBackR.y * h);
      ctx.lineTo(pBackL.x * w, pBackL.y * h);
      ctx.closePath();
      ctx.stroke();

      // 現在まさに打鍵中の場合：鍵盤上にヒットエフェクト & 指番号バッジを表示
      if (currentTime >= n.start && currentTime <= n.end) {
        const hitPoint = this.perspective.mapPoint(uCenter, 0.15);

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
