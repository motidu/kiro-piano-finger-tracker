# Visual Verification Player for L/R Piano MIDI Transcription
> **Interactive Ground-Truth Verifier for Video-Aligned L/R Piano MIDI Transcription**  
> *Kiro University Challenge 2026 Capstone Project*

<details>
<summary>🇯🇵 日本語での概要 (Click to expand / 日本語はこちら)</summary>

このリポジトリは、AI等で演奏動画から生成されたMIDIトランスクリプト（左手・右手分離済み）を、実際の演奏映像と視覚的に重ね合わせ、転写精度を目視検証するための「グラウンドトゥルース検証プレイヤー」です。
- **4隅パースキャリブレーション**: 映像のピアノ鍵盤の4隅（A0〜C8）にピンを合わせて遠近感を補正。
- **L/R左右色分けノート**: 左手（青）・右手（ピンク）のノート落下アニメーションと指番号バッジ（1〜5）を表示。
- **鍵盤ガイド表示切替**: 下層の実際のピアノ鍵盤を見やすくするための表示ON/OFFトグル。
- **Range HTTP サーバー**: RFC 7233準拠のゼロ依存高速ストリーミングサーバーにより、ミリ秒単位のスムーズな動画シークを実現。
</details>

---

## 🎯 The Big Picture Pipeline & Scope

1. **Step 1: Audio-to-MIDI Transcription (External / Upstream)**
   - Extract raw MIDI notes from piano audio using external transcription models (e.g., [ByteDance's piano_transcription](https://github.com/bytedance/piano_transcription)).
   - *Note: Upstream transcription models typically produce a single mixed track without left/right hand separation or fingering.*
2. **Step 2: L/R Hand Separation & Fingering Annotation**
   - **2-1-1. Hand Detection**: Track hands/wrists from video to segment notes into Left/Right tracks.
   - **2-1-2. Visual Verification (★ THIS REPOSITORY)**:  
     Superimpose the separated L/R MIDI notes directly onto the original performance video with 4-corner perspective calibration to **visually verify and ground-truth check if the transcription matches the actual video**.

---

## 🚀 Kiro University Challenge: Complete Syllabus Showcase (Lessons 1–7 + Bonus)

This repository demonstrates the **entire Kiro Agentic IDE workflow**, fulfilling all seven core lessons and bonus requirements:

| Lesson / Milestone | Feature | Implementation in this Repository |
| :--- | :--- | :--- |
| **Lesson 1** | **Spec-Driven Development** | `.kiro/specs/range-http-server/` with EARS notation (`requirements.md`), architectural diagrams (`design.md`), and granular tasks (`tasks.md`). |
| **Lesson 2** | **Steering Documents** | `.kiro/steering/` with persistent constraints (`product.md`, `tech.md`, and `web-viewer.md` for CORS/Audio standards). |
| **Lesson 3** | **Agent Hooks** | `.kiro/hooks/python-syntax-check.json` (`PostFileSave` automatic syntax verification on `.py` edits). |
| **Lesson 4** | **Property-Based Testing (PBT)** | `tests/test_range_http_server.py` using `hypothesis` to fuzz range boundaries and guarantee correctness invariants. |
| **Lesson 5** | **Powers** | `.kiro/powers/range-http-power/` bundling skills, MCP, and stream analysis tools. |
| **Lesson 6** | **Model Context Protocol (MCP)** | `mcp.json` and `.kiro/settings/mcp.json` registering external MCP tool servers. |
| **Lesson 7** | **Custom Agents** | `.kiro/agents/qa-streaming-auditor.json` defining a specialized QA auditor agent with tailored tools, prompts, and permissions. |
| **Bonus 2** | **Package a Kiro Power** | Fully packaged Power manifest `plugin.json` under `.kiro/powers/range-http-power/`. |

---

## ✨ Key Features

- **4-Corner Perspective Calibration**: Real-time quad-warp aligning A0..C8 front/back edges with camera angle.
- **L/R Hand-Separated Falling Notes**: Clean outline-free bars (Blue = Left, Pink = Right) with finger badges (1–5).
- **Toggleable Keyboard Guide**: Hide overlay keyboard (`[🎹 鍵盤ガイド表示]`) to clearly inspect the real video piano keys underneath.
- **High-Precision Range HTTP Streaming Server**: Python zero-dependency server enabling instant smooth video seeking.
- **Full CORS Support**: `Access-Control-Allow-Origin: *` and `OPTIONS` preflight (204 No Content).
- **Robust Security**: Strict path traversal prevention (`resolve()` + `relative_to()`).
- **Zero Runtime Dependencies**: Runs entirely on Python's standard library.

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.11 or later

### Running the Server
```bash
# Serve current directory on port 8080 (default)
python range_http_server.py

# Specify port and custom document root directory
python range_http_server.py --port 8090 --root .
```

### Accessing the Web Verifier
Open `http://localhost:8090/web/` in your browser. Drag and drop your piano performance video (`.mp4`, `.webm`) and L/R MIDI file (`.mid`, `.midi`, or `.json`) to verify alignment.

### Running Tests
Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Run both property-based unit tests and integration tests:
```bash
python -m pytest -v
```

---

## 📂 Repository Structure

```text
.
├── .kiro/
│   ├── agents/
│   │   └── qa-streaming-auditor.json         # Custom Agent config (Lesson 7)
│   ├── hooks/
│   │   └── python-syntax-check.json          # Pre/Post save automated hooks (Lesson 3)
│   ├── powers/
│   │   └── range-http-power/                 # Packaged Kiro Power (Lesson 5 & Bonus 2)
│   │       ├── plugin.json                   # Power manifest
│   │       ├── mcp.json                      # Bundled MCP server
│   │       └── skills/stream-analyzer/       # Bundled Agent skill
│   ├── settings/
│   │   └── mcp.json                          # MCP server configuration (Lesson 6)
│   ├── specs/range-http-server/              # EARS Specs, Design, Tasks (Lesson 1)
│   └── steering/                             # Project Context & Constraints (Lesson 2)
├── mcp.json                                  # Workspace MCP config (Lesson 6)
├── range_http_server.py                      # Main HTTP server implementation
├── web/                                      # Interactive Visual Verification Player
│   ├── index.html                            # Web Viewer UI
│   ├── js/
│   │   ├── main.js                           # App orchestration & timeline
│   │   ├── renderer.js                       # 60fps Canvas falling notes & keyboard
│   │   ├── perspective.js                    # 4-corner calibration & quad warp
│   │   ├── midi_parser.js                    # In-browser Standard MIDI Parser
│   │   └── audio_engine.js                   # Web Audio synth & video pan mixer
│   └── css/
│       └── viewer.css                        # Cyberpunk dark mode styling
├── tests/
│   ├── test_range_http_server.py             # Unit & Property-Based tests (Lesson 4)
│   └── test_integration.py                   # Live server integration tests
├── requirements-dev.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
