# Range HTTP Server (Kiro Challenge Project)

A lightweight, zero-dependency HTTP server with RFC 7233 Range request support, built to power smooth local video/audio streaming and Canvas visualizers without CORS hurdles.

Developed with [Kiro](https://kiro.dev/) as part of the **Kiro University Challenge 2026** final project.

---

## 🚀 Kiro Spec-Driven Development Showcase

This repository serves as a practical demonstration of **Kiro's Spec-driven workflow**, showing how high-reliability systems can be designed and built from formal requirements to automated testing.

### 1. Specs (`.kiro/specs/`) — Lesson 1
Developed using strict EARS (Easy Approach to Requirements Syntax) notation:
- **`requirements.md`**: Complete functional requirements for Range parsing, CORS preflight, error responses, and CLI args.
- **`design.md`**: Architectural breakdown, sequence flows, and formal correctness properties.
- **`tasks.md`**: Step-by-step implementation tasks directly tied to requirement IDs.

### 2. Steering Documents (`.kiro/steering/`) — Lesson 2
Guiding AI code generation with project constraints and domain standards:
- **`tech.md`**: Technical constraints (Python 3.11+, zero external runtime dependencies, Windows/Linux compatibility).
- **`web-viewer.md`**: Standards for Web Audio API & MediaElementSource integration, CORS requirements, and Canvas 60fps streaming.

### 3. Agent Hooks (`.kiro/hooks/`) — Lesson 3
Automating quality assurance during coding:
- **`python-syntax-check.json`**: `PostFileSave` hook that triggers `python -m py_compile` automatically on `.py` edits to prevent syntax regressions.

### 4. Property-Based Testing (PBT) — Lesson 4
Going beyond example-based tests:
- Formal correctness properties are validated using `hypothesis` (in `tests/test_range_http_server.py`), exploring hundreds of arbitrary range intervals and edge-case boundary conditions.

---

## ✨ Features

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
│   ├── hooks/
│   │   └── python-syntax-check.json          # Pre/Post save automated hooks
│   ├── specs/range-http-server/
│   │   ├── requirements.md                   # EARS requirements
│   │   ├── design.md                         # Architecture & correctness properties
│   │   └── tasks.md                          # Implementation tasks
│   └── steering/
│       ├── product.md                        # Product vision
│       ├── tech.md                           # Tech stack constraints
│       └── web-viewer.md                     # Web viewer & CORS guidelines
├── range_http_server.py                      # Main HTTP server implementation
├── tests/
│   ├── test_range_http_server.py             # Unit & Property-Based tests (hypothesis)
│   └── test_integration.py                   # Live server integration tests
├── requirements-dev.txt                      # Test dependencies
├── .gitignore
├── LICENSE                                   # MIT License
└── README.md
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
