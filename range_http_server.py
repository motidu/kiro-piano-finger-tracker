# -*- coding: utf-8 -*-
"""
range_http_server.py — HTTP 206 Partial Content 対応ローカルサーバー

Python 標準ライブラリのみで実装。サードパーティ依存なし。
Requirements: 6.1, 6.2
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import socketserver
import sys
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path


# ---------------------------------------------------------------------------
# 例外クラス
# ---------------------------------------------------------------------------

class RangeNotSatisfiable(Exception):
    """Range ヘッダーが意味的に無効な場合に送出される例外。

    送出条件:
        - start >= file_size
        - start > end
    """


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class RangeSpec:
    """解析済みの Range 情報を保持するデータクラス。

    Attributes:
        start: 0-indexed inclusive バイト開始位置
        end:   0-indexed inclusive バイト終了位置
        total: ファイル全体のバイト数
    """

    start: int
    end: int
    total: int

    @property
    def length(self) -> int:
        """Content-Length に対応する転送バイト数（end - start + 1）。"""
        return self.end - self.start + 1


# ---------------------------------------------------------------------------
# MIME タイプマッピング
# Requirements: 3.1–3.10
# ---------------------------------------------------------------------------

MIME_MAP: dict[str, str] = {
    "mp4":  "video/mp4",
    "webm": "video/webm",
    "mp3":  "audio/mpeg",
    "wav":  "audio/wav",
    "json": "application/json",
    "html": "text/html; charset=utf-8",
    "js":   "application/javascript",
    "css":  "text/css",
}


# ---------------------------------------------------------------------------
# Range ヘッダー解析
# Requirements: 1.1, 1.2, 1.3, 1.6, 7.1, 7.2, 7.3, 7.4
# ---------------------------------------------------------------------------

# Updated regex to capture suffix ranges (bytes=-N)
_RANGE_RE = re.compile(r'^bytes=(\d+)-(\d*)$')
_SUFFIX_RE = re.compile(r'^bytes=-(\d+)$')


def parse_range_header(header: str, file_size: int) -> RangeSpec | None:
    """Range ヘッダー文字列を解析し RangeSpec を返す純粋関数。

    Args:
        header:    "bytes=X-Y", "bytes=X-", または "bytes=-N" 形式の文字列
        file_size: 対象ファイルのバイト数

    Returns:
        RangeSpec(start, end, file_size) — 正常解析時
        None                             — ヘッダーが無効・解析不能（200 OK フォールバック）

    Raises:
        RangeNotSatisfiable — 意味的に無効 (start >= file_size, start > end, suffix_len == 0)
    """
    if not header:
        return None

    # Check for suffix range first (bytes=-N)
    suffix_match = _SUFFIX_RE.match(header)
    if suffix_match:
        suffix_len = int(suffix_match.group(1))
        if suffix_len == 0:
            raise RangeNotSatisfiable("suffix length is 0")
        if suffix_len >= file_size:
            start = 0
            end = file_size - 1
        else:
            start = file_size - suffix_len
            end = file_size - 1
        return RangeSpec(start=start, end=end, total=file_size)

    m = _RANGE_RE.match(header)
    if m is None:
        # パターン不一致 → None (200 OK フォールバック)
        return None

    start = int(m.group(1))
    end_str = m.group(2)

    if end_str == "":
        # bytes=X- 形式（オープンエンド）
        end = file_size - 1
    else:
        end = int(end_str)

    # 意味的バリデーション
    if start >= file_size:
        raise RangeNotSatisfiable(
            f"start ({start}) >= file_size ({file_size})"
        )
    if start > end:
        raise RangeNotSatisfiable(
            f"start ({start}) > end ({end})"
        )

    return RangeSpec(start=start, end=end, total=file_size)


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def _get_mime_type(path: Path) -> str:
    """ファイルパスの拡張子から MIME タイプ文字列を返す。

    拡張子は大文字・小文字を区別しない（`path.suffix.lstrip(".").lower()` で正規化）。
    マッピングに存在しない拡張子、または拡張子なしのファイルは
    ``"application/octet-stream"`` を返す。

    Args:
        path: 対象ファイルの :class:`pathlib.Path`

    Returns:
        RFC 準拠の MIME タイプ文字列

    Requirements: 2.3, 3.1, 3.2–3.10
    """
    ext = path.suffix.lstrip(".").lower()
    return MIME_MAP.get(ext, "application/octet-stream")


# ---------------------------------------------------------------------------
# HTTP リクエストハンドラー
# Requirements: 2.5, 4.1–4.3, 1.1–1.8
# ---------------------------------------------------------------------------


class RangeRequestHandler(BaseHTTPRequestHandler):
    """HTTP 206 Partial Content 対応リクエストハンドラー。

    Class Variables:
        root_dir: 静的ファイルを配信するベースディレクトリ。
                  CLI エントリーポイントで上書きされる。
    """

    root_dir: Path = Path(".")

    # ------------------------------------------------------------------
    # パス解決・セキュリティ
    # Requirements: 2.5
    # ------------------------------------------------------------------

    def _resolve_path(self, url_path: str) -> Path | None:
        """URLパスをファイルシステムの絶対パスに解決し、パストラバーサルを防止する。

        Args:
            url_path: リクエスト URL のパス部分（例: "/video.mp4", "/../../etc/passwd"）

        Returns:
            解決済みの :class:`~pathlib.Path`（ルートディレクトリ内）
            ルートディレクトリ外に出ようとした場合は ``None``（403 Forbidden）

        Requirements: 2.5
        """
        decoded = urllib.parse.unquote(url_path)
        # 先頭スラッシュを除去して Path 結合が正しく機能するようにする
        resolved = (self.__class__.root_dir / decoded.lstrip("/")).resolve()
        # セキュリティチェック: root_dir の外に出ていないか
        try:
            resolved.relative_to(self.__class__.root_dir.resolve())
        except ValueError:
            return None  # パストラバーサル検出 → 403
        return resolved

    # ------------------------------------------------------------------
    # OPTIONS プリフライト対応
    # Requirements: 4.2, 4.3
    # ------------------------------------------------------------------

    def do_OPTIONS(self) -> None:
        """HTTP OPTIONS プリフライトリクエストを処理する。

        `Access-Control-Request-Method` が GET または OPTIONS の場合は
        ``204 No Content`` と CORS ヘッダー 4 種を返す。
        それ以外のメソッドが指定された場合は ``405 Method Not Allowed`` を返す。

        Requirements: 4.2, 4.3
        """
        requested_method = self.headers.get("Access-Control-Request-Method", "GET")
        if requested_method.upper() not in ("GET", "OPTIONS"):
            self.send_response(405)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    # ------------------------------------------------------------------
    # ロギング
    # Requirements: 6.3
    # ------------------------------------------------------------------

    def log_message(self, format: str, *args) -> None:
        """UTF-8 対応ログ出力（標準出力）。

        Requirements: 6.3
        """
        sys.stdout.write(
            "[%s] %s\n" % (self.log_date_time_string(), format % args)
        )
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # レスポンス送信
    # Requirements: 1.1–1.5, 2.1–2.3, 6.4
    # ------------------------------------------------------------------

    def _send_full_response(self, path: Path, mime: str) -> None:
        """ファイル全体を 200 OK で送信する。

        Args:
            path: 送信するファイルの :class:`~pathlib.Path`
            mime: Content-Type に設定する MIME タイプ文字列

        Requirements: 2.1, 2.2, 2.3, 6.4
        """
        file_size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        chunk_size = 65536
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def _send_partial_response(
        self,
        path: Path,
        mime: str,
        start: int,
        end: int,
        total: int,
    ) -> None:
        """指定バイト範囲を 206 Partial Content で送信する。

        Args:
            path:  送信するファイルの :class:`~pathlib.Path`
            mime:  Content-Type に設定する MIME タイプ文字列
            start: 送信開始バイト位置（0-indexed inclusive）
            end:   送信終了バイト位置（0-indexed inclusive）
            total: ファイル全体のバイト数（Content-Range の分母）

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.4
        """
        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        chunk_size = 65536
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                chunk = f.read(to_read)
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    # ------------------------------------------------------------------
    # エラーレスポンス送信ヘルパー
    # Requirements: 4.1
    # ------------------------------------------------------------------

    def _send_error_response(self, code: int, message: str) -> None:
        """エラーレスポンスを送信する汎用ヘルパー。

        すべてのエラーレスポンスに ``Access-Control-Allow-Origin: *`` を付与する。

        Args:
            code:    HTTP ステータスコード（例: 403, 404, 500）
            message: レスポンスボディに含めるエラーメッセージ（UTF-8 エンコード）

        Requirements: 4.1
        """
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # GET リクエスト処理
    # Requirements: 1.1–1.8, 2.1–2.5, 4.1, 6.3, 6.4
    # ------------------------------------------------------------------

    def do_GET(self) -> None:
        """HTTP GET リクエストを処理する。

        処理フロー:
        1. URL パスをパース（クエリ文字列を除去）
        2. `_resolve_path()` でパストラバーサルチェック → None なら 403
        3. ファイル存在確認 → 存在しなければ 404
        4. `_get_mime_type()` で Content-Type 決定
        5. Range ヘッダーの有無を確認:
           - 無し        → `_send_full_response()` (200 OK)
           - 有り・正常  → `_send_partial_response()` (206 Partial Content)
           - 有り・None  → `_send_full_response()` (200 OK フォールバック)
           - 有り・無効  → 416 Range Not Satisfiable
        6. OSError → 500 Internal Server Error

        Requirements: 1.1–1.8, 2.1–2.5, 4.1, 6.3, 6.4
        """
        # クエリ文字列を除去してパスのみ取得
        url_path = urllib.parse.urlparse(self.path).path

        try:
            # 1. パストラバーサルチェック
            resolved = self._resolve_path(url_path)
            if resolved is None:
                self._send_error_response(403, "403 Forbidden: Access denied.")
                return

            # 2. ファイル存在確認
            if not resolved.is_file():
                self._send_error_response(404, f"404 Not Found: {url_path}")
                return

            # 3. MIME タイプ判別
            mime = _get_mime_type(resolved)

            # 4. ファイルサイズ取得
            file_size = resolved.stat().st_size

            # 5. Range ヘッダーの有無で分岐
            range_header = self.headers.get("Range")

            if range_header is None:
                # Range ヘッダーなし → 200 OK で全体レスポンス
                self._send_full_response(resolved, mime)
                return

            # Range ヘッダーあり → 解析
            try:
                rs = parse_range_header(range_header, file_size)
            except RangeNotSatisfiable:
                # 意味的に無効な Range → 416
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            if rs is None:
                # 解析不能（パターン不一致） → 200 OK フォールバック
                self._send_full_response(resolved, mime)
            else:
                # 正常解析 → 206 Partial Content
                self._send_partial_response(resolved, mime, rs.start, rs.end, rs.total)

        except (BrokenPipeError, ConnectionResetError):
            # クライアントが切断した場合（動画シークやタブ終了など）はエラーとせず終了
            return
        except OSError as exc:
            self._send_error_response(500, f"500 Internal Server Error: {exc}")

    # ------------------------------------------------------------------
    # HEAD リクエスト処理
    # Requirements: 1.1–1.8, 2.1–2.3, 4.1, 6.4
    # ------------------------------------------------------------------

    def do_HEAD(self) -> None:
        """HTTP HEAD リクエストを処理する。

        GET と同じヘッダーを返すが、ボディは含まない。

        Requirements: 1.1–1.8, 2.1–2.3, 4.1, 6.4
        """
        url_path = urllib.parse.urlparse(self.path).path

        try:
            # 1. パストラバーサルチェック
            resolved = self._resolve_path(url_path)
            if resolved is None:
                self._send_error_response(403, "403 Forbidden: Access denied.")
                return

            # 2. ファイル存在確認
            if not resolved.is_file():
                self._send_error_response(404, f"404 Not Found: {url_path}")
                return

            # 3. MIME タイプ判別
            mime = _get_mime_type(resolved)

            # 4. ファイルサイズ取得
            file_size = resolved.stat().st_size

            # 5. Range ヘッダーの有無で分岐
            range_header = self.headers.get("Range")

            if range_header is None:
                # Range ヘッダーなし → 200 OK ヘッダーのみ
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            # Range ヘッダーあり → 解析
            try:
                rs = parse_range_header(range_header, file_size)
            except RangeNotSatisfiable:
                # 意味的に無効な Range → 416
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            if rs is None:
                # 解析不能（パターン不一致） → 200 OK フォールバック
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
            else:
                # 正常解析 → 206 Partial Content ヘッダーのみ
                length = rs.end - rs.start + 1
                self.send_response(206)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", f"bytes {rs.start}-{rs.end}/{rs.total}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

        except (BrokenPipeError, ConnectionResetError):
            return
        except OSError as exc:
            self._send_error_response(500, f"500 Internal Server Error: {exc}")


# ---------------------------------------------------------------------------
# CLI エントリーポイント
# Requirements: 5.1–5.8, 6.2, 6.3, 6.5
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    def _port_type(value: str) -> int:
        """argparse 用ポート番号バリデーター。

        Args:
            value: コマンドライン引数として渡された文字列

        Returns:
            検証済みの整数ポート番号（1–65535）

        Raises:
            argparse.ArgumentTypeError: 整数でない、または 1–65535 の範囲外の場合

        Requirements: 5.8
        """
        try:
            port = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Port must be an integer, got: {value!r}"
            )
        if not (1 <= port <= 65535):
            raise argparse.ArgumentTypeError(
                f"Port must be 1–65535, got: {port}"
            )
        return port

    parser = argparse.ArgumentParser(
        description="HTTP 206 Partial Content 対応ローカルサーバー"
    )
    parser.add_argument(
        "root_dir",
        nargs="?",
        default=str(Path.cwd()),
        help="配信ルートディレクトリ (default: カレントディレクトリ)",
    )
    parser.add_argument(
        "-p", "--port",
        type=_port_type,
        default=8090,
        help="TCPポート番号 1–65535 (default: 8090)",
    )
    args = parser.parse_args()

    # ルートディレクトリのバリデーション
    # Requirements: 5.3, 5.4, 5.7
    root = Path(args.root_dir).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Error: '{root}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    # UTF-8 stdout 設定
    # Requirements: 6.3
    sys.stdout.reconfigure(encoding="utf-8")

    # ハンドラーにルートディレクトリを設定
    RangeRequestHandler.root_dir = root

    # allow_reuse_address をクラスレベルで設定（bind 前に反映させるため）
    # Requirements: 5.6
    socketserver.TCPServer.allow_reuse_address = True

    # サーバー起動
    # Requirements: 5.1, 5.2, 5.5, 5.6, 6.2, 6.3
    try:
        with socketserver.ThreadingTCPServer(
            ("127.0.0.1", args.port), RangeRequestHandler
        ) as server:
            print(f"Serving on http://127.0.0.1:{args.port}")
            sys.stdout.flush()
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                # シャットダウンログ
                # Requirements: 6.3
                print("\nShutting down server...", flush=True)
                server.shutdown()
    except OSError as e:
        # ポート使用中など
        # Requirements: 5.6, 6.5
        print(
            f"Error: Could not start server on port {args.port}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
