# Range HTTP Server (Kiro Challenge Project)

A lightweight, zero-dependency HTTP server with RFC 7233 Range request support, built to power smooth local video/audio streaming and Canvas visualizers without CORS hurdles.

Developed with [Kiro](https://kiro.dev/) as part of the **Kiro University Challenge 2026** final project.

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

## ✨ Server Features

- **RFC 7233 / 9110 Compliant Range Requests**:
  - Explicit ranges: `bytes=0-499`
  - Open-ended ranges: `bytes=500-`
  - Suffix byte ranges: `bytes=-500` (last 500 bytes)
  - `206 Partial Content` with `Content-Range: bytes START-END/TOTAL`
  - `416 Range Not Satisfiable` for out-of-bounds requests
- **High-Performance Streaming**: 64KB chunked streaming avoids loading large video files into RAM.
- **Full CORS Support**: Universal `Access-Control-Allow-Origin: *` and `OPTIONS` preflight (204 No Content).
- **HEAD Method Support**: RFC-compliant header-only inspection for downloaders and media probes.
- **Robust Security**: Strict path traversal prevention (`resolve()` + `relative_to()`), neutralizing `../` and URL-encoded attacks.
- **Graceful Disconnects**: Silently handles client-side aborts (`BrokenPipeError`, `ConnectionResetError`) without polluting server logs.
- **Zero Runtime Dependencies**: Runs entirely on Python's standard library (`http.server`, `urllib`, `pathlib`, `argparse`).

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.11 or later

### Running the Server
```bash
# Serve current directory on port 8080 (default)
python range_http_server.py

# Specify port and custom document root directory
python range_http_server.py --port 8090 --root ./media
```

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
