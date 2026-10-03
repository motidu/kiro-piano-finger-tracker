---
inclusion: fileMatch
fileMatchPattern: ["**/*.html", "**/*.js", "**/range_http_server.py"]
---

# Piano Overlay & Web Audio Viewer Standards

## 1. Web Audio & Media Sync Rules
- **Autoplay & Resume Policy**:
  - `AudioContext` はブラウザの自動再生ポリシーにより初期状態で `suspended` になるため、再生ボタン押下（初回のユーザーアクション）契機で確実に `audioCtx.resume()` を呼び出すこと。
- **CORS & Audio Routing**:
  - 動画音声のパンニングに `createMediaElementSource(video)` を使用する場合、`file://` プロトコルでは Origin が不透明（opaque）となり無音化される。必ずローカルHTTPサーバー（`http://127.0.0.1:8090/` 等）を経由して配信・検証すること。
- **Seeking & Range Request**:
  - `<video>` タグでのタイムシーク操作時に先頭（0:00）へリセットされる問題を防ぐため、バックエンド側は必ず `HTTP 206 Partial Content (Accept-Ranges: bytes)` に対応したサーバーを使用すること。

## 2. Canvas & Perspective Calibration Rules
- **High-Performance Rendering Loop**:
  - `requestAnimationFrame` による 60fps ループを維持し、`video.currentTime` を唯一の真実（Single Source of Truth）としてノーツ落下位置を同期すること。
- **4-Corner Bilinear Perspective Mapping**:
  - 鍵盤の幾何学座標は、4点 P0（A0手前）, P1（C8手前）, P2（C8奥）, P3（A0奥）を用いた双線形補間（Bilinear Interpolation）で算出すること。
  - 描画負荷を抑えるため、鍵盤ごとの正規化幅 `u` や台形変換ロジックは毎フレーム無駄にオブジェクト生成を行わず、最適化された関数で処理すること。
- **Persistence & Touch-Free Mode**:
  - キャリブレーション座標は `localStorage` に保持し、リロード後も即座に復元すること。
  - 演奏確認時はドラッグピンや補助グリッド線を非表示（トグル切替）にでき、純粋なノーツ描画のみにできる設計を維持すること。

## 3. Data Architecture Rules
- **Zero-Inline Bloat**:
  - 数千音に及ぶ MIDI/採譜データ（notes JSON）は HTML/JS 内にインラインでハードコードせず、必ず外部 JSON（`ray_notes.json`）から非同期 `fetch` で読み込む構成を維持すること。