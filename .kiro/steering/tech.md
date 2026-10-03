# Technology Stack & System Constraints

## 1. Execution Environment & Hardware
- **OS & Shell**: Windows 11 (PowerShell / pwsh)
- **Primary GPU**: NVIDIA GeForce RTX 4070 Ti SUPER (16GB VRAM, CUDA Toolkit 12.x)
- **Languages**:
  - Python 3.11+ / 3.14 (GPU推論、動画/音声処理、MIDI解析、ローカルサーバー)
  - HTML5 / Modern JavaScript (ES6+) (Webブラウザ上のリアルタイム描画、Web Audio API音響合成)
- **Local LLM Engine**: Strata (llama-server / Swift 1.5 125B MoE)
- **File Encoding**: すべてのPythonスクリプト、HTML、JSONは UTF-8 を厳守すること。

## 2. Core Libraries & Pipeline Modules
- **Audio Transcription**:
  - `piano_transcription_inference` (PyTorch + CUDA によるポリフォニック音響採譜)
  - `mido`: MIDI解析、トラック分離、チック/秒単位の変換
  - `librosa`, `soundfile`: WAV音声抽出・正規化
- **Computer Vision & Video**:
  - `mediapipe` (v1.0+ Task API / HandLandmarker による21点骨格キーポイント抽出)
  - `opencv-python` (`cv2`): フレーム展開、鍵盤領域・運指トラッキング
  - `yt-dlp`, `ffmpeg`: 動画/音声ダウンロードおよびストリーム処理
- **Inspection Web Viewer**:
  - HTML5 Canvas 2D: 60fps ノーツ落下アニメーション、88鍵パースペクティブ描画
  - Web Audio API: `AudioContext`, `StereoPannerNode`, `OscillatorNode` (元音声とMIDIシンセ音のリアルタイムL/Rパン比較)
  - `range_http_server.py`: 大容量動画のシークに対応する HTTP 206 Partial Content 準拠サーバー

## 3. Strict Technical Constraints (Absolute Rules)
1. **Local-First & Execution Isolation**:
   - 外部プラットフォーム（YouTube等）のBot判定・IPブロックを回避するため、クラウド環境（Google Colab等）ではなく、必ずローカル RTX 4070 Ti SUPER 上でパイプラインを完結させること。
2. **Media Streaming & Origin Security**:
   - Chromium の CORS/Origin 仕様により `file://` 直開きでは `createMediaElementSource` が無音化するため、必ずローカル配信（`http://127.0.0.1:8090/`）を前提とすること。
   - 一般的な簡易サーバー（`http.server`）ではシーク時に再生位置が先頭に戻るため、HTTP `Range` リクエスト（HTTP 206）を完全サポートした実装を維持すること。
3. **Geometric Accuracy (Bilinear Perspective Mapping)**:
   - カメラの台形歪みに対処するため、単純な矩形オフセットではなく4隅（P0: A0手前, P1: C8手前, P2: C8奥, P3: A0奥）を指定した双線形補間（Bilinear Interpolation）で88鍵の正確な位置を算出すること。
4. **Data Optimization & Separation**:
   - 音符データ（数千ノーツ）をHTMLにインライン展開せず、独立したメタデータ（`ray_notes.json`）として外部化し、非同期 `fetch` でロードすること。