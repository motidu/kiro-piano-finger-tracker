# -*- coding: utf-8 -*-
"""
tests/test_range_http_server.py — range_http_server のテストスイート

pytest によるユニットテスト。
Checkpoint 4: parse_range_header() と _get_mime_type() の全ケースをカバー。
"""

import pytest
from pathlib import Path

from range_http_server import (
    RangeNotSatisfiable,
    RangeSpec,
    _get_mime_type,
    parse_range_header,
)


# ---------------------------------------------------------------------------
# parse_range_header() — ユニットテスト
# Tasks: 2.6
# ---------------------------------------------------------------------------

class TestParseRangeHeaderNormal:
    """正常系: 有効な Range ヘッダーが RangeSpec を返す。"""

    def test_explicit_range(self):
        """bytes=100-199 → start=100, end=199, length=100"""
        result = parse_range_header("bytes=100-199", 1000)
        assert result is not None
        assert result.start == 100
        assert result.end == 199
        assert result.length == 100

    def test_open_ended_from_zero(self):
        """bytes=0- (file_size=1000) → start=0, end=999, length=1000"""
        result = parse_range_header("bytes=0-", 1000)
        assert result is not None
        assert result.start == 0
        assert result.end == 999
        assert result.length == 1000

    def test_open_ended_last_byte(self):
        """bytes=999- (file_size=1000) → start=999, end=999, length=1"""
        result = parse_range_header("bytes=999-", 1000)
        assert result is not None
        assert result.start == 999
        assert result.end == 999
        assert result.length == 1

    def test_total_stored_in_rangespec(self):
        """RangeSpec.total にファイルサイズが格納される。"""
        result = parse_range_header("bytes=0-499", 1000)
        assert result is not None
        assert result.total == 1000

    def test_length_property(self):
        """RangeSpec.length は end - start + 1 に等しい。"""
        result = parse_range_header("bytes=50-149", 500)
        assert result is not None
        assert result.length == result.end - result.start + 1

    def test_single_byte_range(self):
        """bytes=5-5 → start=5, end=5, length=1"""
        result = parse_range_header("bytes=5-5", 100)
        assert result is not None
        assert result.start == 5
        assert result.end == 5
        assert result.length == 1

    def test_suffix_range(self):
        """bytes=-500 (file_size=1000) → start=500, end=999, length=500"""
        result = parse_range_header("bytes=-500", 1000)
        assert result is not None
        assert result.start == 500
        assert result.end == 999
        assert result.length == 500

    def test_suffix_range_full(self):
        """bytes=-1000 (file_size=1000) → start=0, end=999, length=1000"""
        result = parse_range_header("bytes=-1000", 1000)
        assert result is not None
        assert result.start == 0
        assert result.end == 999
        assert result.length == 1000

    def test_suffix_range_exceeds(self):
        """bytes=-2000 (file_size=1000) → start=0, end=999, length=1000"""
        result = parse_range_header("bytes=-2000", 1000)
        assert result is not None
        assert result.start == 0
        assert result.end == 999
        assert result.length == 1000


class TestParseRangeHeaderInvalid:
    """異常系: RangeNotSatisfiable が送出される。"""

    def test_start_equals_file_size(self):
        """bytes=1000- (file_size=1000) → RangeNotSatisfiable"""
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header("bytes=1000-", 1000)

    def test_start_exceeds_file_size(self):
        """bytes=9999- で小さいファイル → RangeNotSatisfiable"""
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header("bytes=9999-", 500)

    def test_start_greater_than_end(self):
        """bytes=200-100 → RangeNotSatisfiable"""
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header("bytes=200-100", 1000)

    def test_suffix_zero_length(self):
        """bytes=-0 → RangeNotSatisfiable"""
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header("bytes=-0", 1000)


class TestParseRangeHeaderFallback:
    """フォールバック系: None を返し 200 OK にフォールバックする。"""

    def test_invalid_format_string(self):
        """"invalid" → None"""
        assert parse_range_header("invalid", 1000) is None

    def test_empty_string(self):
        """空文字列 → None"""
        assert parse_range_header("", 1000) is None

    def test_wrong_unit(self):
        """bytes 以外の単位 → None"""
        assert parse_range_header("items=0-100", 1000) is None

    def test_non_numeric_start(self):
        """bytes=abc-def → None"""
        assert parse_range_header("bytes=abc-def", 1000) is None

    def test_space_in_header(self):
        """スペース含む → None"""
        assert parse_range_header("bytes= 0-100", 1000) is None


# ---------------------------------------------------------------------------
# _get_mime_type() — ユニットテスト
# Tasks: 3.3
# ---------------------------------------------------------------------------

class TestGetMimeTypeKnownExtensions:
    """既知の8拡張子が正しい MIME タイプにマッピングされる。"""

    def test_mp4(self):
        assert _get_mime_type(Path("video.mp4")) == "video/mp4"

    def test_webm(self):
        assert _get_mime_type(Path("video.webm")) == "video/webm"

    def test_mp3(self):
        assert _get_mime_type(Path("audio.mp3")) == "audio/mpeg"

    def test_wav(self):
        assert _get_mime_type(Path("audio.wav")) == "audio/wav"

    def test_json(self):
        assert _get_mime_type(Path("data.json")) == "application/json"

    def test_html(self):
        assert _get_mime_type(Path("index.html")) == "text/html; charset=utf-8"

    def test_js(self):
        assert _get_mime_type(Path("app.js")) == "application/javascript"

    def test_css(self):
        assert _get_mime_type(Path("style.css")) == "text/css"


class TestGetMimeTypeCaseInsensitive:
    """大文字・混在ケースでも同一 MIME タイプを返す。"""

    def test_uppercase_mp4(self):
        assert _get_mime_type(Path("video.MP4")) == "video/mp4"

    def test_mixed_case_json(self):
        assert _get_mime_type(Path("data.Json")) == "application/json"

    def test_all_uppercase_webm(self):
        assert _get_mime_type(Path("video.WEBM")) == "video/webm"

    def test_mixed_case_html(self):
        assert _get_mime_type(Path("page.HTML")) == "text/html; charset=utf-8"


class TestGetMimeTypeFallback:
    """未知拡張子・拡張子なしは application/octet-stream を返す。"""

    def test_unknown_extension(self):
        assert _get_mime_type(Path("archive.xyz")) == "application/octet-stream"

    def test_no_extension(self):
        assert _get_mime_type(Path("README")) == "application/octet-stream"

    def test_binary_extension(self):
        assert _get_mime_type(Path("program.exe")) == "application/octet-stream"

    def test_tar_gz(self):
        assert _get_mime_type(Path("archive.gz")) == "application/octet-stream"


# ---------------------------------------------------------------------------
# _resolve_path() — ユニットテスト
# Tasks: 5.2
# Requirements: 2.5
# ---------------------------------------------------------------------------

import tempfile
from unittest.mock import MagicMock
from range_http_server import RangeRequestHandler


def _make_handler(root_dir: Path) -> RangeRequestHandler:
    """HTTP機構を迂回して _resolve_path テスト用の最小ハンドラーを生成する。"""
    handler = RangeRequestHandler.__new__(RangeRequestHandler)
    RangeRequestHandler.root_dir = root_dir
    return handler


class TestResolvePath:
    """_resolve_path() のセキュリティ・正常系テスト。"""

    def test_path_traversal_dotdot(self, tmp_path):
        """../../etc/passwd → None（パストラバーサル検出 → 403）"""
        handler = _make_handler(tmp_path)
        result = handler._resolve_path("../../etc/passwd")
        assert result is None

    def test_path_traversal_url_encoded(self, tmp_path):
        """%2e%2e%2f%2e%2e%2fetc%2fpasswd → None（URLエンコード済みトラバーサル）"""
        handler = _make_handler(tmp_path)
        result = handler._resolve_path("%2e%2e%2f%2e%2e%2fetc%2fpasswd")
        assert result is None

    def test_normal_path_returns_path_object(self, tmp_path):
        """/video.mp4 → root_dir 内の Path オブジェクト（ファイルの存在不問）"""
        handler = _make_handler(tmp_path)
        result = handler._resolve_path("/video.mp4")
        assert result is not None
        assert isinstance(result, Path)
        # root_dir の内側に収まっていること
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_root_path_returns_root_dir(self, tmp_path):
        """/ → root_dir 自身を返す"""
        handler = _make_handler(tmp_path)
        result = handler._resolve_path("/")
        assert result is not None
        assert result == tmp_path.resolve()
