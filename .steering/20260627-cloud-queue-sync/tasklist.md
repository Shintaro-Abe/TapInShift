# クラウドキュー同期 タスクリスト

## 1. ステアリング

- [x] `.steering/20260627-cloud-queue-sync/` を作成する。
- [x] `requirements.md` を作成する。
- [x] `design.md` を作成する。
- [x] `tasklist.md` を作成する。

## 2. 方針確認

- [x] Windows 端末停止中でも Slack 操作を受け付ける方針にする。
- [x] Excel 反映は Windows Agent 起動後の同期処理で行う方針にする。
- [x] クラウドには最小限の打刻、メモ、編集データだけ保存する。
- [x] Excel ファイルと Excel password はクラウドに保存しない。
- [x] Slack App は HTTP Request URL 方式へ切り替える。
- [x] Windows Agent はクラウド API を定期ポーリングする。
- [x] 二重反映防止として claim 方式を採用する。
- [x] AWS Lambda Function URL + DynamoDB を採用する。
- [x] DynamoDB は単一テーブル構成にする。
- [x] 丸め設定も同じ DynamoDB テーブルに保存する。
- [x] Windows Agent のポーリング間隔は 5 分にする。
- [x] 手動同期コマンドを用意する。
- [x] 初回範囲に出勤、退勤、メモ反映、丸め設定、編集モーダルを含める。
- [x] 編集モーダルは上書き操作として扱い、空欄項目は既存値を保持する。
- [x] Slack App Home の状態表示は最小限にする。

## 3. クラウド基盤

- [x] AWS Lambda 用の実装ディレクトリ構成を決める。
- [x] Lambda Function URL のルーティング設計を決める。
- [x] DynamoDB `TapInShiftEvents` テーブル定義を実装する。
- [x] 未同期取得用 GSI を定義する。
- [x] AWS デプロイ方式を決める。
- [x] ローカル開発で Lambda 相当のテストを実行できるようにする。

## 4. Slack HTTP 受付

- [x] Slack 署名検証を実装する。
- [x] Slack URL verification に対応する。
- [x] App Home 表示イベントを処理する。
- [x] 出勤ボタン操作を処理する。
- [x] 退勤ボタン操作を処理する。
- [x] メモ反映操作を処理する。
- [x] 丸め単位 select 操作を処理する。
- [x] 日付選択と編集モーダル表示を処理する。
- [x] 編集モーダル送信を処理する。
- [x] Slack への ack 応答時間を守る。

## 5. クラウド業務ロジック

- [x] Slack 操作受付時に `tapped_at` を確定する。
- [x] クラウド側で `reflected_at` を丸め計算する。
- [x] 出勤/退勤別の丸め方向を適用する。
- [x] 任意メモ分類をクラウド側で実行する。
- [x] 出退勤イベントを DynamoDB に保存する。
- [x] メモ反映イベントを DynamoDB に保存する。
- [x] 日別編集イベントを DynamoDB に保存する。
- [x] 丸め設定を DynamoDB に保存する。
- [x] 同日同種の二重打刻を検出し、Slack に警告する。
  - [x] 同日同種の既存打刻を検出する純粋ロジックを追加する。
  - [x] 検出結果を Slack App Home の警告表示へ接続する。
- [x] `needs_confirmation` の扱いを実装する。

## 6. 同期 API

- [x] Windows Agent 用 Bearer token 認証を実装する。
- [x] `queued` イベントの claim API を実装する。
- [x] claim 成功時に `claimed` イベントを返す API を実装する。
- [x] 同期成功報告 API を実装する。
- [x] 同期失敗報告 API を実装する。
- [x] `claimed` 期限切れイベントを再同期対象に戻す処理を実装する。
- [x] リトライ可能失敗とリトライ不可失敗を区別する。

## 7. Windows Agent 同期

- [x] クラウド同期設定を `config` に追加する。
- [x] 同期 token を環境変数から読み込む。
- [x] `sync-now` コマンドを追加する。
- [x] 起動直後の同期処理を追加する。
- [x] 5 分ごとのポーリング処理を追加する。
- [x] claim 済み出退勤イベントを Excel へ反映する。
- [x] claim 済みメモ反映イベントを Excel へ反映する。
- [x] claim 済み日別編集イベントを Excel へ反映する。
- [x] ローカル SQLite に同期試行履歴を保存する。
- [x] 同期結果をクラウド API へ返す。

## 8. Excel 反映

- [x] クラウド由来の `reflected_at` を丸め直さず Excel に書き込む。
- [x] 打刻時の既存セル上書き防止を維持する。
- [x] 日別編集では入力あり項目だけ上書きする。
- [x] 日別編集の空欄項目は既存 Excel 値を保持する。
- [x] Excel 反映失敗を同期 API へ返す形式に整理する。

## 9. テスト

- [x] Slack 署名検証の単体テストを追加する。
- [x] DynamoDB アイテム変換の単体テストを追加する。
- [x] 丸め結果固定の単体テストを追加する。
- [x] 任意メモ分類結果保存の単体テストを追加する。
- [x] claim 状態遷移の単体テストを追加する。
- [x] `claimed` 期限切れ復旧の単体テストを追加する。
- [x] Windows Agent 同期処理の単体テストを追加する。
- [x] Excel writer 既存テストをクラウド由来イベントに合わせて拡張する。
- [x] Slack App Home 表示のテストをクラウド側へ追加する。

## 10. ドキュメント

- [x] `docs/product-requirements.md` をクラウドキュー同期構成に合わせて更新する。
- [x] `docs/functional-design.md` をクラウド受付、同期 API、Windows Agent に合わせて更新する。
- [x] `docs/architecture.md` を AWS Lambda Function URL + DynamoDB 構成に合わせて更新する。
- [x] `docs/glossary.md` にクラウドキュー、claim、同期状態を追加する。
- [x] Slack App 設定手順を HTTP Request URL 方式に更新する。
- [x] AWS 側の秘密情報設定手順を追加する。
- [x] Windows Agent の同期起動手順を追加する。

## 11. 検証

- [x] ローカルテストを全件実行する。
- [x] Lambda 相当のローカル HTTP 受付を検証する。
- [x] DynamoDB または代替ローカルストアでイベント保存を検証する。
- [ ] Slack App Home がクラウド側で表示されることを確認する。
- [x] Windows Agent 停止中に Slack でイベントを受け付けられることを確認する。
- [x] Windows Agent 起動後に未同期イベントが Excel へ反映されることを確認する。
- [x] 二重打刻時の Slack 警告と Excel 上書き防止を確認する。
- [x] 失敗時にクラウド DB とローカル SQLite の両方へ履歴が残ることを確認する。

## 12. 完了条件

- [x] Windows 端末停止中でも Slack 操作が受け付けられる。
- [x] 受け付けたイベントが DynamoDB に保存される。
- [x] Windows Agent 起動後に未同期イベントが Excel へ反映される。
- [ ] 出勤、退勤、メモ反映、日別編集、丸め設定がクラウド経由で動作する。
- [x] 二重反映防止が claim 方式で機能する。
- [x] ローカル SQLite 監査ログが残る。
- [x] 関連する `docs/` が現状仕様と一致している。
- [x] 秘密情報、Excel ファイル、SQLite が Git 管理対象に含まれていない。

## 13. 実行ログ

### 2026-06-28 ローカル実行

- [x] `PYTHONPATH=src python3 -m unittest discover -s tests` を実行し、85件 PASS を確認した。
- [x] 一時venv `/tmp/tapinshift-run-venv` に依存関係を導入し、CLI 起動可能な状態を確認した。
- [x] `tapinshift-agent --config config/config.example.json --check-config` を実行し、未設定の Slack token、Excel password、クラウド同期 endpoint/token が不足として表示されることを確認した。
- [x] `tapinshift-agent --config config/config.example.json --sync-now` を実行し、`TAPINSHIFT_CLOUD_ENDPOINT` 未設定時に明確なエラーで停止することを確認した。
- [x] AWS CLI v2 を `.tools/` に導入し、AWS 認証を確認した。
- [x] CloudFormation スタック `tapinshift-cloud` を作成し、Lambda Function URL と DynamoDB をデプロイした。
- [x] Lambda Function URL `/health` が `{"ok": true}` を返すことを確認した。
- [x] `.env.local` に `TAPINSHIFT_CLOUD_ENDPOINT` を設定した。
- [x] `tapinshift-agent --config config/config.example.json --sync-now` を実行し、クラウド同期APIへ接続できることを確認した。未同期イベントなしのため結果は `0` 件。
- [x] Slack App の Events URL / Interactivity URL 設定を実施した。
- [x] Slack App から出勤・退勤を送信し、DynamoDB に `queued` の `punch` イベント2件が保存されることを確認した。
- [x] `tapinshift-agent --config config/config.example.json --sync-now` を実行し、2件を claim して処理することを確認した。
- [x] このLinux環境では `TAPINSHIFT_EXCEL_PASSWORD` が未設定のため、DynamoDB では2件が `failed`、ローカルSQLiteでも `failed` として記録されることを確認した。
- [x] Windows 実機で `tapinshift-agent --config config\config.local.json --sync-now` を実行し、`INFO: Cloud sync reflected attempt count: 2` を確認した。
- [x] DynamoDB 上で出勤・退勤2件が `reflected` に更新され、`error` が空であることを確認した。
- [x] Lambda の Slack 受付時刻が AWS 実行環境の UTC に依存しないよう、`Asia/Tokyo` で保存されるよう修正し、デプロイした。
- [x] 日本時間確認用に作成した同日重複のテスト打刻4件を `failed` / `retryable=false` に更新し、Excel反映対象から除外した。
- [x] Windowsログオン時に `--poll-cloud` を起動するタスクスケジューラ登録batを追加した。
- [x] Windows 実機での `--poll-cloud` 常駐同期を実行し、出勤・退勤が `reflected` になることを確認した。
- [x] Windows再起動後もStartup登録経由でクラウド同期Agentが動作することを確認した。
