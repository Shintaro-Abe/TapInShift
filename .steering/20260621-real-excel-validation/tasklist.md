# 実 Excel 検証 タスクリスト

## 1. ステアリング

- [x] `.steering/20260621-real-excel-validation/` を作成する。
- [x] `requirements.md` を作成する。
- [x] `design.md` を作成する。
- [x] `tasklist.md` を作成する。

## 2. 事前確認

- [x] `git status --short` で作業ツリーを確認する。
- [x] 実勤務表が Git 管理対象外のパスにあることを確認する。
- [x] 実勤務表の検証用コピーを作成する。
- [ ] 原本で確認する必要がある場合は、復元可能なバックアップを作成する。
- [x] `excel.path` が原本ではなく検証用コピー、またはバックアップ作成済みファイルを指す方針であることを確認する。
- [x] `config/config.local.json` が Git 管理対象外であることを確認する。
- [x] Excel パスワードをファイルに保存していないことを確認する。

## 3. 実行環境セットアップ

- [x] Python 3.11 以上を使えることを確認する。
- [x] 仮想環境を作成する。
- [x] 仮想環境を有効化する。
- [x] `pip install -e .` を実行する。
- [x] `tapinshift-agent --help` が実行できることを確認する。
- [x] 実機では `xlwings` が同じ仮想環境に導入されていることを確認する。

## 4. ローカル設定

- [x] `config/config.example.json` から `config/config.local.json` を作成する。
- [x] `excel.path` を検証用コピーのローカルパスに設定する。
- [x] `excel.sheet_name` が `6` であることを確認する。
- [x] `excel.first_data_row` が `7`、`excel.last_data_row` が `37` であることを確認する。
- [x] 日付列 `L`、出勤 `F`、退勤 `G`、届出 `W`、経費 `Y`、金額 `AB` を確認する。
- [x] 既定値 `B=1`, `C=1`, `D=0`, `E=0` を確認する。

## 5. 環境変数

- [x] `SLACK_BOT_TOKEN` を設定する。
- [x] `SLACK_APP_TOKEN` を設定する。
- [x] `TAPINSHIFT_EXCEL_PASSWORD` を設定する。
- [ ] OpenAI 分類を使う場合は `OPENAI_API_KEY` を設定する。
- [x] OpenAI 分類を使わない場合はローカルルールフォールバックで動くことを確認する。

## 6. Slack App 設定

- [x] Socket Mode が有効であることを確認する。
- [x] App Home が有効であることを確認する。
- [x] Interactivity が有効であることを確認する。
- [x] `app_home_opened` イベントを購読していることを確認する。
- [x] App Home 表示に必要な Bot token scope が付与されていることを確認する。
- [x] モーダル表示に必要な Bot token scope が付与されていることを確認する。

## 7. 品質チェック

- [x] `PYTHONPATH=src python3 -m unittest discover -s tests` を実行する。
- [x] `tapinshift-agent --config config/config.local.json --check-config` を実行する。
- [x] `--check-config` の `MISSING` または `OK` が期待どおりであることを確認する。

## 8. 実機 Excel 検証

- [x] 実機検証用ランブック `.steering/20260621-real-excel-validation/validation-runbook.md` を作成する。
- [x] 検証作業の自動化スクリプトを作成する（`scripts/setup-local.*`, `scripts/check-local.*`, `scripts/validate-local.*`, `scripts/timesheet_tools.py`, `slack-app-manifest.example.yml`）。
- [x] 実機検証ランブックを HTML 化し、コードブロックをコピー可能にする（`validation-runbook.html`, `scripts/render_runbook_html.py`）。
- [x] Windows または macOS の実機で Python 環境を用意する。
- [x] 実機に `xlwings` を導入する。
- [x] Excel アプリで検証用コピーを開けることを確認する。
- [x] エージェントからパスワード付き勤務表を開けることを確認する。
- [x] 出勤操作で対象日の `F` 列へ時刻が反映されることを確認する。
- [x] 退勤操作で対象日の `G` 列へ時刻が反映されることを確認する。
- [x] メモ分類の検証モードが OpenAI API かローカルルールかを記録する。
  - 現時点の検証基準はローカルルール。OpenAI API を使う場合も金額は `amount` のみに入れ、届出内容と経費内容は分離する。
- [x] 届出内容の検証用メモ例と期待値を決める。
  - `遅延証明あり` -> `W=遅延証明あり`
  - `遅延証明あり 交通費1200円` -> `W=遅延証明あり`, `Y=交通費`, `AB=1200`
- [x] 経費内容・金額の検証用メモ例と期待値を決める。
  - `交通費320円` -> `Y=交通費`, `AB=320`
  - `交通費1200円 遅延証明あり` -> `W=遅延証明あり`, `Y=交通費`, `AB=1200`
- [x] 任意メモから届出内容が `W` 列へ期待どおり反映されることを確認する。
- [x] 任意メモから経費内容が `Y` 列、金額が `AB` 列へ期待どおり反映されることを確認する。
- [x] 空欄の既定項目に `B=1`, `C=1`, `D=0`, `E=0` が入ることを確認する。
- [x] 既存の出勤または退勤セルがある場合、打刻で上書きされないことを確認する。

## 9. Slack UI 検証

- [x] Slack App Home が表示されることを確認する。
- [x] 出勤ボタンを押して App Home の状態表示が更新されることを確認する。
- [x] 退勤ボタンを押して App Home の状態表示が更新されることを確認する。
- [x] 丸め単位を選択し、以降の出勤・退勤に適用されることを確認する。
- [x] 日付選択から編集モーダルが開くことを確認する。
- [x] 編集モーダル保存後、選択日の Excel セルが上書きされることを確認する。
- [x] 反映失敗時に Slack 上で復旧判断できる文言が表示されることを確認する。

## 10. SQLite 確認

- [x] 打刻成功時に `reflected` として保存されることを確認する。
- [x] 分類確認待ち時に `needs_confirmation` として保存されることを確認する。
- [x] Excel 反映失敗時に `failed` とエラー内容が保存されることを確認する。
- [x] 手動編集履歴が追記保存されることを確認する。
- [x] 丸め単位の選択値が `app_settings` に保存されることを確認する。

## 11. 修正判断

- [x] 実勤務表の日付セル形式が合わない場合、`excel_writer.py` の日付正規化を修正する。
- [x] Excel 書き込み値の型が想定と違う場合、時刻・金額の変換を修正する。
- [x] Slack UI の入力値が実運用に不足する場合、`slack_app.py` とテストを修正する。
- [x] 基本設計に影響する修正が出た場合、該当する `docs/` を更新する。

### 適用済み修正（2026-06-22 コードレビュー）

- [x] 編集モーダル保存時のデータ損失対策: `excel_writer._apply_day_values` を追加し、空欄(None)の項目は既存 Excel セルを上書きしない方針に変更（`service.py` 経由）。`slack_app.py` のモーダル説明文も「空欄は既存値を保持」に更新。
- [x] 反映時刻の秒・μ秒除去: `excel_writer._excel_time_text` を追加し、`write_punch` の `F/G` 書き込みを `HH:MM` 文字列に統一。
- [x] 手動編集の金額パース改善: `service._to_int_or_none` でカンマ・`円`・`¥` を除去（`"abc"` 等は引き続き失敗）。
- [x] 追加テスト: `tests/test_excel_writer.py`（空欄保持・分丸め・日番号/Excelシリアル/曜日付き文字列検索・対象日なし・Excel password 未設定）、`tests/test_service.py`（カンマ・円付き金額、丸め設定、`needs_confirmation`、writer 失敗）、`tests/test_config.py`（丸め方向読み込み）、`tests/test_storage.py`（`app_settings`）、`tests/test_slack_app.py`（丸め単位 select・失敗文言）、`tests/test_timesheet_tools.py`（`show-db` の `app_settings` 互換表示・allowlist 表示）、`tests/test_classifier.py`（複合メモ分離）。全39件 PASS。
- [x] `show-db` の `app_settings` 表示を allowlist 化し、現時点では `time_rounding.mode` のみ表示する。
- [x] Codex レビュー方式を `AGENTS.md` と `docs/codex-review-workflow.md` に整理した。
- [x] 実勤務表 `L` 列が日番号の場合にも対象日を検索できるよう、`excel_writer._find_row` の日付判定を修正する。
- [x] 出退勤の時刻丸めを設定できるよう、`time_rounding.clock_in_direction` / `clock_out_direction` を追加。既定は丸めなし、出勤切り上げ・退勤切り捨てを設定可能にした。
- [x] Slack App Home から丸め単位（なし/5/10/15/20/30分）を選択できるようにし、選択値を SQLite に保存する。
- [x] 複合メモを `W/Y/AB` へ分離するローカル分類ルールを追加する。
- [ ] 2回目打刻が `W/Y/AB` を上書きする挙動は運用判断後に対応（現状は許容）。

## 12. 完了条件

- [ ] 検証用コピーまたは復元可能なバックアップを使って実 Excel 検証している。
- [x] 実勤務表で出勤、退勤、手動編集の正常系が確認済みである。
- [x] 既存セル上書き防止、対象日なし、パスワード未設定などの失敗系が確認済みである。
- [x] SQLite に成功、確認待ち、失敗、手動編集履歴が保存されることを確認済みである。
- [x] SQLite に丸め単位設定が保存され、再起動後も利用されることを確認済みである。
- [x] 秘密情報、実勤務表、SQLite が Git 管理対象に含まれていない。
- [x] コード修正が発生した場合、関連テストが完了している。
