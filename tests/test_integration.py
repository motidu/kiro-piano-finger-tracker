# -*- coding: utf-8 -*-
"""
tests/test_integration.py — range_http_server の統合テスト

テストサーバーをバックグラウンドスレッドで起動し、
GET(200), Range(206), Out-of-bounds(416), Path traversal(403/404), OPTIONS(204) を検証する。
"""

import threading
import socket
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
import socketserver
import pytest

from range_http_server import RangeRequestHandler


def _find_free_port() -> int:
    """利用可能な TCP ポート番号を取得する。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_test_server(root_dir: Path, port: int) -> socketserver.ThreadingTCPServer:
    """テスト用 RangeRequestHandler サーバーを起動する。"""
    RangeRequestHandler.root_dir = root_dir
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), RangeRequestHandler)
    server.allow_reuse_address = True
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.fixture(scope="module")
def test_server():
    """テストサーバーとテストファイルを作成し、テスト後にシャットダウンする。"""
    tmp_dir = Path(tempfile.mkdtemp())
    # テスト用ファイルを作成
    test_file = tmp_dir / "test_video.mp4"
    test_file.write_bytes(b"A" * 1000)  # 1000 bytes

    port = _find_free_port()
    server = _start_test_server(tmp_dir, port)

    yield server, port, tmp_dir

    server.shutdown()
    server.server_close()


def test_get_full_file(test_server):
    """GET リクエストで 200 OK とファイル全体が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)

    assert resp.status == 200
    assert resp.headers["Content-Type"] == "video/mp4"
    assert resp.headers["Content-Length"] == "1000"
    assert resp.headers["Accept-Ranges"] == "bytes"
    assert resp.headers["Access-Control-Allow-Origin"] == "*"

    body = resp.read()
    assert len(body) == 1000
    assert body == b"A" * 1000


def test_range_request_206(test_server):
    """Range ヘッダー付き GET で 206 Partial Content が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    req.add_header("Range", "bytes=100-199")

    resp = urllib.request.urlopen(req)

    assert resp.status == 206
    assert resp.headers["Content-Type"] == "video/mp4"
    assert resp.headers["Content-Length"] == "100"
    assert resp.headers["Content-Range"] == "bytes 100-199/1000"
    assert resp.headers["Accept-Ranges"] == "bytes"
    assert resp.headers["Access-Control-Allow-Origin"] == "*"

    body = resp.read()
    assert len(body) == 100
    assert body == b"A" * 100


def test_range_open_ended(test_server):
    """bytes=500- (オープンエンド) で 206 が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    req.add_header("Range", "bytes=500-")

    resp = urllib.request.urlopen(req)

    assert resp.status == 206
    assert resp.headers["Content-Length"] == "500"
    assert resp.headers["Content-Range"] == "bytes 500-999/1000"

    body = resp.read()
    assert len(body) == 500


def test_range_out_of_bounds_416(test_server):
    """start >= file_size の Range で 416 Range Not Satisfiable が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    req.add_header("Range", "bytes=1000-1100")

    try:
        urllib.request.urlopen(req)
        assert False, "Expected 416 response"
    except urllib.error.HTTPError as e:
        assert e.code == 416
        assert e.headers["Content-Range"] == "bytes */1000"
        assert e.headers["Accept-Ranges"] == "bytes"
        assert e.headers["Access-Control-Allow-Origin"] == "*"


def test_range_start_exceeds_file_size_416(test_server):
    """start > file_size の Range で 416 が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    req.add_header("Range", "bytes=2000-3000")

    try:
        urllib.request.urlopen(req)
        assert False, "Expected 416 response"
    except urllib.error.HTTPError as e:
        assert e.code == 416


def test_path_traversal_attack(test_server):
    """パストラバーサル攻撃で 403 Forbidden が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/../../etc/passwd"

    try:
        urllib.request.urlopen(url)
        assert False, "Expected 403 response"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        assert e.headers["Access-Control-Allow-Origin"] == "*"


def test_path_traversal_url_encoded(test_server):
    """URLエンコードされたパストラバーサル攻撃で 403 が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/%2e%2e%2f%2e%2e%2fetc%2fpasswd"

    try:
        urllib.request.urlopen(url)
        assert False, "Expected 403 response"
    except urllib.error.HTTPError as e:
        assert e.code == 403


def test_file_not_found_404(test_server):
    """存在しないファイルで 404 Not Found が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/nonexistent.mp4"

    try:
        urllib.request.urlopen(url)
        assert False, "Expected 404 response"
    except urllib.error.HTTPError as e:
        assert e.code == 404
        assert e.headers["Access-Control-Allow-Origin"] == "*"


def test_options_preflight_204(test_server):
    """OPTIONS プリフライトで 204 No Content と CORS ヘッダーが返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url, method="OPTIONS")
    req.add_header("Access-Control-Request-Method", "GET")

    resp = urllib.request.urlopen(req)

    assert resp.status == 204
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert "GET" in resp.headers["Access-Control-Allow-Methods"]
    assert "OPTIONS" in resp.headers["Access-Control-Allow-Methods"]
    assert resp.headers["Access-Control-Allow-Headers"] == "Range"
    assert resp.headers["Access-Control-Max-Age"] == "86400"


def test_options_preflight_invalid_method(test_server):
    """OPTIONS プリフライトで GET/OPTIONS 以外のメソッド指定時、405 が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url, method="OPTIONS")
    req.add_header("Access-Control-Request-Method", "DELETE")

    try:
        urllib.request.urlopen(req)
        assert False, "Expected 405 response"
    except urllib.error.HTTPError as e:
        assert e.code == 405
        assert e.headers["Access-Control-Allow-Origin"] == "*"


def test_chunked_streaming_large_file(test_server):
    """大きなファイルの 64KB チャンクストリーミングが正しく動作することを検証する。"""
    server, port, tmp_dir = test_server

    # 大きなファイルを作成 (1MB = 1048576 bytes)
    large_file = tmp_dir / "large_file.mp4"
    large_file.write_bytes(b"B" * 1048576)

    url = f"http://127.0.0.1:{port}/large_file.mp4"

    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)

    assert resp.status == 200
    assert resp.headers["Content-Length"] == "1048576"

    body = resp.read()
    assert len(body) == 1048576
    assert body == b"B" * 1048576


def test_head_full_file(test_server):
    """HEAD リクエストで 200 OK とヘッダーが返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url, method="HEAD")
    resp = urllib.request.urlopen(req)

    assert resp.status == 200
    assert resp.headers["Content-Type"] == "video/mp4"
    assert resp.headers["Content-Length"] == "1000"
    assert resp.headers["Accept-Ranges"] == "bytes"
    assert resp.headers["Access-Control-Allow-Origin"] == "*"

    # HEAD should have no body
    body = resp.read()
    assert len(body) == 0


def test_head_range_request_206(test_server):
    """Range ヘッダー付き HEAD で 206 Partial Content ヘッダーが返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url, method="HEAD")
    req.add_header("Range", "bytes=100-199")

    resp = urllib.request.urlopen(req)

    assert resp.status == 206
    assert resp.headers["Content-Type"] == "video/mp4"
    assert resp.headers["Content-Length"] == "100"
    assert resp.headers["Content-Range"] == "bytes 100-199/1000"
    assert resp.headers["Accept-Ranges"] == "bytes"
    assert resp.headers["Access-Control-Allow-Origin"] == "*"

    body = resp.read()
    assert len(body) == 0


def test_head_suffix_range_206(test_server):
    """Range ヘッダー付き HEAD (suffix) で 206 Partial Content ヘッダーが返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url, method="HEAD")
    req.add_header("Range", "bytes=-100")

    resp = urllib.request.urlopen(req)

    assert resp.status == 206
    assert resp.headers["Content-Length"] == "100"
    assert resp.headers["Content-Range"] == "bytes 900-999/1000"

    body = resp.read()
    assert len(body) == 0


def test_suffix_range_request_206(test_server):
    """Range ヘッダー付き GET (suffix) で 206 Partial Content が返されることを検証する。"""
    server, port, tmp_dir = test_server
    url = f"http://127.0.0.1:{port}/test_video.mp4"

    req = urllib.request.Request(url)
    req.add_header("Range", "bytes=-100")

    resp = urllib.request.urlopen(req)

    assert resp.status == 206
    assert resp.headers["Content-Type"] == "video/mp4"
    assert resp.headers["Content-Length"] == "100"
    assert resp.headers["Content-Range"] == "bytes 900-999/1000"

    body = resp.read()
    assert len(body) == 100
    assert body == b"A" * 100
