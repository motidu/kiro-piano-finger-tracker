# Implementation Plan: range_http_server

## Overview

`range_http_server.py` を Python 標準ライブラリのみで実装する。コアの純粋関数（`parse_range_header`、`_get_mime_type`）から始め、ハンドラークラス、CLI エントリーポイントの順に組み立てる。テストは `pytest` + `hypothesis` を用い、各実装タスクに隣接してプロパティテスト・ユニットテストを配置する。

## Tasks

- [x] 1. プロジェクト構造とコア型の定義
  - `range_http_server.py` を作成し、モジュール先頭に UTF-8 エンコーディング宣言と標準ライブラリのみの import を記述する
  - `RangeNotSatisfiable(Exception)` 例外クラスを定義する
  - `RangeSpec` データクラス（`start: int`, `end: int`, `total: int`, `length` プロパティ）を定義する
  - `MIME_MAP: dict[str, str]` を定義する（mp4, webm, mp3, wav, json, html, js, css の 8 エントリー）
  - `tests/` ディレクトリと空の `tests/__init__.py`、`tests/test_range_http_server.py` を作成する
  - _Requirements: 6.1, 6.2, 3.1_

- [x] 2. `parse_range_header()` の実装とテスト
  - [x] 2.1 `parse_range_header(header: str, file_size: int) -> RangeSpec | None` を実装する
    - `bytes=X-Y` および `bytes=X-` の正規表現マッチ
    - 不正形式は `None` を返す（200 OK フォールバック）
    - `start >= file_size` または `start > end` の場合は `RangeNotSatisfiable` を送出
    - 正常時は `RangeSpec(start, end, file_size)` を返す
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 7.1, 7.2, 7.3, 7.4_

  - [x]* 2.2 Property 1: Range ヘッダー解析ラウンドトリップ
    - **Property 1: Range ヘッダーの解析ラウンドトリップ**
    - `hypothesis` で `file_size`, `start`, `end` を生成し `bytes=X-Y` のパースが `(X, Y)` かつ `length == Y - X + 1` を返すことを検証
    - **Validates: Requirements 1.1, 7.1**

  - [x]* 2.3 Property 2: オープンエンド Range 展開不変性
    - **Property 2: オープンエンド Range の展開不変性**
    - `bytes=X-` が `(X, file_size - 1)` かつ `length == file_size - X` を返すことを検証（`X = 0` を含む）
    - **Validates: Requirements 1.2, 1.3, 7.2**

  - [x]* 2.4 Property 4: 意味的に無効な Range → RangeNotSatisfiable
    - **Property 4: 意味的に無効な Range は常に 416 を返す**
    - `start >= file_size` の入力で常に `RangeNotSatisfiable` が送出されることを検証
    - **Validates: Requirements 1.6, 7.4**

  - [x]* 2.5 Property 5: 不正形式 Range → None
    - **Property 5: 不正形式 Range ヘッダーは 200 OK にフォールバックする**
    - `bytes=\d*-\d*` にマッチしない文字列が `None` を返すことを検証
    - **Validates: Requirements 7.3**

  - [x]* 2.6 `parse_range_header()` ユニットテスト
    - `bytes=100-199` → `(100, 199)`, length=100
    - `bytes=0-` (file_size=1000) → `(0, 999)`, length=1000
    - `bytes=999-` (file_size=1000) → `(999, 999)`, length=1
    - `bytes=1000-` (file_size=1000) → `RangeNotSatisfiable`
    - `bytes=200-100` → `RangeNotSatisfiable`
    - `"invalid"` → `None`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 3. `_get_mime_type()` の実装とテスト
  - [x] 3.1 `_get_mime_type(path: Path) -> str` を実装する
    - `path.suffix.lstrip(".").lower()` で拡張子を正規化してから `MIME_MAP` をルックアップ
    - 未知拡張子・拡張子なしは `"application/octet-stream"` を返す
    - _Requirements: 2.3, 3.1, 3.2–3.10_

  - [x]* 3.2 Property 6: MIME タイプ ケースインセンシティブ不変性
    - **Property 6: MIME タイプ判別のケースインセンシティブ不変性**
    - `hypothesis` で各拡張子のランダム大文字化バリアントを生成し、常に同じ MIME 文字列を返すことを検証
    - **Validates: Requirements 2.3, 3.1**

  - [x]* 3.3 `_get_mime_type()` ユニットテスト
    - 8 拡張子（mp4, webm, mp3, wav, json, html, js, css）の正常マッピング
    - 大文字・混在ケース（`MP4`, `Json`）→ 同一 MIME
    - 未知拡張子 `.xyz` → `application/octet-stream`
    - 拡張子なし `README` → `application/octet-stream`
    - _Requirements: 3.1–3.10_

- [x] 4. Checkpoint — ここまでのテストをすべて pass させること
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. `RangeRequestHandler` のパス解決・エラー応答の実装
  - [x] 5.1 `_resolve_path(url_path: str) -> Path | None` を実装する
    - `urllib.parse.unquote` でデコード後、`Path(root_dir / url_path).resolve()` でルートディレクトリ外チェック
    - ルート外なら `None`（403）
    - _Requirements: 2.5_

  - [x] 5.2 パストラバーサルのユニットテスト（任意）
    - `../../etc/passwd` → `None`
    - 正常パス → `Path` オブジェクト
    - _Requirements: 2.5_

  - [x] 5.3 `do_OPTIONS()` を実装する
    - `204 No Content` + CORS ヘッダー 4 種（`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`, `Access-Control-Max-Age`）を送信
    - `GET`/`OPTIONS` 以外のメソッドには `405 Method Not Allowed`
    - _Requirements: 4.2, 4.3_

  - [x] 5.4 `_send_full_response()` および `_send_partial_response()` を実装する
    - `_send_full_response`: `200 OK` + `Content-Type`, `Content-Length`, `Accept-Ranges`, `Access-Control-Allow-Origin: *`
    - `_send_partial_response`: `206 Partial Content` + `Content-Type`, `Content-Length`, `Content-Range`, `Accept-Ranges`, `Access-Control-Allow-Origin: *`
    - どちらもファイルをバイナリモードで読み込んで送信
    - _Requirements: 1.1–1.5, 2.1–2.3, 6.4_

  - [x] 5.5 `do_GET()` を実装する（各メソッドの組み合わせ）
    - パス解決 → MIME 判別 → Range ヘッダー有無の分岐 → `_send_full_response` / `_send_partial_response` / `416`
    - `OSError` は `500 Internal Server Error`
    - すべてのレスポンスに `Access-Control-Allow-Origin: *` を付与
    - `log_message()` を UTF-8 対応にオーバーライド
    - _Requirements: 1.1–1.8, 2.1–2.5, 4.1, 6.3, 6.4_

- [x] 6. Content-Range フォーマット整合性テスト
  - [x]* 6.1 Property 3: Content-Range ヘッダーフォーマット整合性
    - **Property 3: Content-Range ヘッダーのフォーマット整合性**
    - 有効な `(start, end, total)` に対してフォーマットした文字列が `"bytes {start}-{end}/{total}"` であり、再パースで元の値が復元されることを検証
    - **Validates: Requirements 1.4, 7.5**

- [x] 7. CLI エントリーポイントの実装
  - [x] 7.1 `__main__` ブロックを実装する
    - `argparse` で `root_dir`（positional, default=CWD）と `--port`/`-p`（default=8090）を定義
    - ルートディレクトリの存在・ディレクトリ判定（失敗 → stderr + exit 1）
    - ポート範囲バリデーション 1–65535 外 → exit 2
    - `sys.stdout.reconfigure(encoding="utf-8")`
    - `ThreadingTCPServer(("127.0.0.1", port), RangeRequestHandler)` 生成
    - `Serving on http://127.0.0.1:<port>` を stdout に出力
    - `KeyboardInterrupt` で `server.shutdown()` を呼びシャットダウンログを出力
    - ポート使用中は `OSError` をキャッチし stderr + exit 1
    - _Requirements: 5.1–5.8, 6.2, 6.3, 6.5_

- [x] 8. HTTP 統合テスト
  - [x]* 8.1 統合テスト（インプロセス HTTP サーバー）
    - `threading.Thread` でサーバーを起動し `http.client.HTTPConnection` でリクエスト送信
    - 以下のシナリオをカバー：
      - `200 OK`（Range なし）: 全体レスポンス、`Content-Length` 一致
      - `206 Partial Content`（有効 Range）: 指定バイト範囲のみ返却
      - `416`（`Range: bytes=9999-`、小さいファイル）
      - `404`（存在しないパス）
      - `403`（パストラバーサルパス）
      - `OPTIONS`（プリフライト）: 204 + CORS ヘッダー確認
      - 全レスポンスに `Access-Control-Allow-Origin: *` が含まれることを確認
    - _Requirements: 1.1–1.8, 2.1–2.5, 4.1–4.3_

  - [x]* 8.2 Property 7: CORS ヘッダーユニバーサル付与
    - **Property 7: CORS ヘッダーのユニバーサル付与**
    - すべてのステータスコード（200, 206, 403, 404, 416）のレスポンスに `Access-Control-Allow-Origin: *` が含まれることを検証
    - **Validates: Requirements 4.1**

  - [x]* 8.3 Property 8: バイナリファイルラウンドトリップ整合性
    - **Property 8: バイナリファイルのラウンドトリップ整合性**
    - 任意のバイト列をファイルに書き込み、`200 OK` または `bytes=0-` の `206` レスポンスがそのバイト列を変更なく返すことを検証
    - **Validates: Requirements 6.4**

- [x] 9. Final Checkpoint — 全テスト pass・スモークテスト確認
  - Ensure all tests pass, ask the user if questions arise.
  - `python range_http_server.py --help` が終了コード 0 で完了することを確認
  - サードパーティ依存が存在しないことを `importlib.metadata` 等で確認（テストコードの `hypothesis` / `pytest` を除く）

## Notes

- `*` 付きのサブタスクはオプション（MVP では省略可）
- 各タスクは対応する requirements を明示してトレーサビリティを確保
- `hypothesis` は **テストコード専用** の依存であり、本体 `range_http_server.py` への依存は禁止（Requirements 6.1 準拠）
- プロパティテストは `max_examples=200` で実行すること（design.md 参照）
- 統合テストはインプロセスサーバー（`threading.Thread`）を使用し、ポートの衝突を避けるためランダムポートまたは固定テスト用ポートを使用すること

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.6", "3.2", "3.3"] },
    { "id": 3, "tasks": ["5.1", "5.2", "5.3", "5.4", "6.1"] },
    { "id": 4, "tasks": ["5.5"] },
    { "id": 5, "tasks": ["7.1"] },
    { "id": 6, "tasks": ["8.1", "8.2", "8.3"] }
  ]
}
```
