---
name: range-stream-analyzer
description: Skill for validating RFC 7233 byte-range responses and chunked video streaming latency.
---

# Range Stream Analyzer Skill

Use this skill when auditing or debugging HTTP 206 Partial Content streams and CORS headers.

## Verification Checklist
1. Send `Range: bytes=0-100` and ensure `206 Partial Content` with `Content-Range: bytes 0-100/TOTAL`.
2. Send `Range: bytes=-500` (suffix) and ensure last 500 bytes are returned.
3. Send `Range: bytes=1000000-` and ensure `416 Range Not Satisfiable` with `Content-Range: bytes */TOTAL`.
4. Send `OPTIONS` preflight and verify `204 No Content` with `Access-Control-Allow-Origin: *`.
