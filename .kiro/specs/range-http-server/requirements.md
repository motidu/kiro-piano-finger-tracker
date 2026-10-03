# Requirements Document

## Introduction

`range_http_server.py` は、Piano Finger Tracker & Visualizer プロジェクトにおいて、Webブラウザ上で大容量の演奏動画（MP4等）をシームレスに再生・シークするためのローカルHTTPサーバーモジュールである。

Python 標準ライブラリの `http.server` は HTTP Range リクエスト（RFC 7233）をサポートしないため、`<video>` タグでのシーク操作が先頭（0:00）にリセットされる問題がある。また、Chromium の CORS/Origin 制約により `file://` プロトコルでは `createMediaElementSource` が無音化するため、必ず `http://127.0.0.1:8090/` 経由での配信が必要となる。

本モジュールは `HTTP 206 Partial Content` と `Accept-Ranges: bytes` を完全実装し、サードパーティライブラリに依存せず Python 標準ライブラリのみで動作する。

## Glossary

- **Server**: `range_http_server.py` として実装されるローカルHTTPサーバープロセス
- **Client**: サーバーにリクエストを送信するWebブラウザ（Chromium 系ブラウザを主対象とする）
- **Range_Request**: HTTP `Range: bytes=X-Y` ヘッダーを含むHTTPリクエスト（RFC 7233 準拠）
- **Partial_Response**: HTTP ステータス `206 Partial Content` を返す部分コンテンツレスポンス
- **Full_Response**: HTTP ステータス `200 OK` を返す完全コンテンツレスポンス
- **Root_Directory**: サーバーが静的ファイルを配信するベースディレクトリ
- **MIME_Type**: ファイル拡張子に基づいて決定されるコンテンツタイプ文字列
- **CORS_Header**: クロスオリジンリソース共有を許可するHTTPレスポンスヘッダー（`Access-Control-Allow-Origin`）
- **Port**: サーバーがリッスンするTCPポート番号（デフォルト: 8090）

---

## Requirements

### Requirement 1: HTTP Range リクエストへの部分レスポンス

**User Story:** 動画プレイヤーを使用するユーザーとして、動画の任意の時点にシークしたとき、再生位置が先頭にリセットされずにその位置から再生が始まることを望む。

#### Acceptance Criteria

1. WHEN the Client sends a request containing a `Range: bytes=X-Y` header, THE Server SHALL return a `206 Partial Content` response containing only the bytes from position X to position Y (inclusive), with a `Content-Length` header equal to `Y - X + 1`.
2. WHEN the Client sends a `Range: bytes=X-` header with no end boundary, THE Server SHALL return a `206 Partial Content` response from byte X to the last byte of the file, with a `Content-Length` header equal to `total file size - X`.
3. WHEN the Client sends a `Range: bytes=0-` header, THE Server SHALL return a `206 Partial Content` response containing the full file content with a `Content-Length` header equal to the total file size.
4. THE Server SHALL include a `Content-Range: bytes X-Y/Z` header in every `206 Partial Content` response, where X and Y reflect the actual bytes served and Z is the total file size in bytes.
5. THE Server SHALL include an `Accept-Ranges: bytes` header in every `200 OK`, `206 Partial Content`, and `416 Range Not Satisfiable` response.
6. WHEN the Client sends a `Range` header with a start byte value greater than or equal to the total file size, THE Server SHALL return a `416 Range Not Satisfiable` response with a `Content-Range: bytes */Z` header and an empty response body.
7. WHEN the Client sends a request without a `Range` header, THE Server SHALL return a `200 OK` response with the full file content.
8. IF a requested file path does not exist, THE Server SHALL return a `404 Not Found` response.

---

### Requirement 2: 通常ファイルの完全レスポンス

**User Story:** ブラウザクライアントとして、Range ヘッダーなしでファイルをリクエストしたとき、ファイル全体を受け取ることを望む。

#### Acceptance Criteria

1. WHEN the Client sends a request without a `Range` header, THE Server SHALL return a `200 OK` response containing the complete file content.
2. WHEN the Server returns a `200 OK` response, THE Server SHALL include a `Content-Length` header equal to the total file size in bytes.
3. WHEN the Server returns a `200 OK` response, THE Server SHALL include a `Content-Type` header determined by the file extension of the requested path.
4. IF a requested file path does not exist within the Root_Directory, THEN THE Server SHALL return a `404 Not Found` response with an error message in the response body.
5. IF a requested path resolves to a location outside the Root_Directory, THEN THE Server SHALL return a `403 Forbidden` response with an error message in the response body.

---

### Requirement 3: MIME タイプの自動判別

**User Story:** Webブラウザを使用するユーザーとして、動画・音声・テキストファイルが正しい Content-Type で配信されることを望む。

#### Acceptance Criteria

1. THE Server SHALL determine the `Content-Type` response header for each response by extracting the file extension as the substring after the last `.` character, matched case-insensitively.
2. IF the file extension is `.mp4`, THEN THE Server SHALL set the `Content-Type` header to `video/mp4`.
3. IF the file extension is `.webm`, THEN THE Server SHALL set the `Content-Type` header to `video/webm`.
4. IF the file extension is `.mp3`, THEN THE Server SHALL set the `Content-Type` header to `audio/mpeg`.
5. IF the file extension is `.wav`, THEN THE Server SHALL set the `Content-Type` header to `audio/wav`.
6. IF the file extension is `.json`, THEN THE Server SHALL set the `Content-Type` header to `application/json`.
7. IF the file extension is `.html`, THEN THE Server SHALL set the `Content-Type` header to `text/html; charset=utf-8`.
8. IF the file extension is `.js`, THEN THE Server SHALL set the `Content-Type` header to `application/javascript`.
9. IF the file extension is `.css`, THEN THE Server SHALL set the `Content-Type` header to `text/css`.
10. IF the file extension does not match any defined type, OR the filename contains no `.` character, THEN THE Server SHALL set the `Content-Type` header to `application/octet-stream`.

---

### Requirement 4: CORS ヘッダーの付与

**User Story:** Webブラウザ上で動作するスクリプトを使用するユーザーとして、ローカルサーバーへのクロスオリジンリクエストがブロックされずに成功することを望む。

#### Acceptance Criteria

1. THE Server SHALL include the header `Access-Control-Allow-Origin: *` in every HTTP response, regardless of the response status code (2xx, 3xx, 4xx, or 5xx).
2. WHEN the Client sends an HTTP `OPTIONS` preflight request with `Access-Control-Request-Method` set to `GET` or `OPTIONS`, THE Server SHALL return a `204 No Content` response containing all of the following headers: `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, OPTIONS`, `Access-Control-Allow-Headers: Range`, and `Access-Control-Max-Age: 86400`.
3. IF the Client sends an HTTP `OPTIONS` preflight request with `Access-Control-Request-Method` set to a value other than `GET` or `OPTIONS`, THEN THE Server SHALL return a `405 Method Not Allowed` response with an error message indicating the method is not permitted.

---

### Requirement 5: 起動設定（ポートおよびルートディレクトリ）

**User Story:** 開発者として、異なるプロジェクトディレクトリや別のポートでサーバーを起動できることを望む。

#### Acceptance Criteria

1. THE Server SHALL accept a command-line argument `--port` (or `-p`) to specify the Port.
2. THE Server SHALL default to Port `8090` when the `--port` argument is not provided.
3. THE Server SHALL accept a positional command-line argument specifying the Root_Directory path.
4. THE Server SHALL default to the current working directory when the positional argument is not provided.
5. WHEN the Server starts successfully, THE Server SHALL print the listening address in the format `Serving on http://127.0.0.1:<port>` to standard output.
6. IF the specified Port is already in use, THEN THE Server SHALL print an error message indicating the Port conflict to standard error and exit with a non-zero exit code.
7. IF the specified Root_Directory path does not exist, OR the path exists but is not a directory, THEN THE Server SHALL print an error message to standard error and exit with a non-zero exit code.
8. IF the specified Port value is not an integer in the range 1–65535, THEN THE Server SHALL print an error message to standard error and exit with a non-zero exit code.

---

### Requirement 6: 標準ライブラリ単独実装と UTF-8 エンコーディング

**User Story:** 開発者として、追加パッケージのインストールなしに任意の Python 3.11+ 環境でサーバーを即座に起動できることを望む。

#### Acceptance Criteria

1. THE Server SHALL be implemented using only Python standard library modules, with no third-party package dependencies.
2. THE Server SHALL be executable directly with `python range_http_server.py` on Python 3.11 or later.
3. THE Server SHALL reconfigure standard output to UTF-8 encoding at startup, and SHALL log at minimum the following events: server start (with address), each incoming request (method and path), and server shutdown.
4. THE Server SHALL read and serve all files in binary mode to preserve exact byte content regardless of file type.
5. IF the Port is already in use at startup, THE Server SHALL write an error message to standard error using UTF-8 encoding and exit with a non-zero exit code.

---

### Requirement 7: パーサー・シリアライザの整合性（Range ヘッダー解析）

**User Story:** 開発者として、Range ヘッダーの解析が正確であり、あらゆる有効な形式を正しく処理できることを望む。

#### Acceptance Criteria

1. WHEN the Client sends a valid `Range: bytes=X-Y` header where X and Y are non-negative integers and `X <= Y`, THE Range_Parser SHALL parse the header into integer start value X and integer end value Y.
2. WHEN the Client sends a valid `Range: bytes=X-` header where X is a non-negative integer and `X < file_size`, THE Range_Parser SHALL parse the header into integer start value X and an end value equal to the last byte index of the file (`file_size - 1`).
3. IF the `Range` header value does not match the pattern `bytes=\d*-\d*`, THEN THE Range_Parser SHALL treat the request as a non-Range request and return a `200 OK` response with the full file body and a `Content-Length` header equal to `file_size`.
4. IF the `Range` header matches the pattern `bytes=\d*-\d*` but is semantically invalid (X > Y, or X >= file_size), THEN THE Range_Parser SHALL return a `416 Range Not Satisfiable` response.
5. WHEN the Client sends a valid `Range: bytes=X-Y` header and THE Server returns a `206 Partial Content` response, THE Server SHALL include a `Content-Range` header with the exact value `bytes X-Y/file_size`.
