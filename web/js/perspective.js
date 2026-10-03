// web/js/perspective.js
// 4点ピンによる鍵盤の透視投影（アングル補正）

export class PerspectiveMapper {
  constructor() {
    // P0: 左前, P1: 右前, P2: 右奥, P3: 左奥 (0.0〜1.0)
    this.points = {
      P0: { x: 0.05, y: 0.92 },
      P1: { x: 0.95, y: 0.92 },
      P2: { x: 0.88, y: 0.65 },
      P3: { x: 0.12, y: 0.65 }
    };
    this.loadFromStorage();
  }

  loadFromStorage() {
    const saved = localStorage.getItem("piano_perspective_points");
    if (saved) {
      try {
        this.points = JSON.parse(saved);
      } catch (e) {
        console.warn("Perspective restore failed", e);
      }
    }
  }

  saveToStorage() {
    localStorage.setItem("piano_perspective_points", JSON.stringify(this.points));
  }

  /**
   * u: 鍵盤の横位置 (0: 最低音A0 〜 1: 最高音C8)
   * v: 奥行き (0: 手前・白鍵先端 〜 1: 奥・落ち物発生ライン)
   */
  mapPoint(u, v) {
    const { P0, P1, P2, P3 } = this.points;

    // 手前の線上の補間
    const frontX = P0.x + (P1.x - P0.x) * u;
    const frontY = P0.y + (P1.y - P0.y) * u;

    // 奥の線上の補間
    const backX = P3.x + (P2.x - P3.x) * u;
    const backY = P3.y + (P2.y - P3.y) * u;

    // 奥行き v に応じた線形補間
    const x = frontX + (backX - frontX) * v;
    const y = frontY + (backY - frontY) * v;

    return { x, y };
  }

  setPoint(key, x, y) {
    if (this.points[key]) {
      this.points[key] = { x, y };
      this.saveToStorage();
    }
  }
}
