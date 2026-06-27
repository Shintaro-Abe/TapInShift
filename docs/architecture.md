# TapInShift 技術仕様書

## 1. 技術概要

TapInShift は Python で実装されたローカル常駐エージェントである。Slack Socket Mode で Slack App と接続し、ユーザー操作を受けて SQLite へ監査ログを保存し、xlwings 経由でローカル Excel 勤務表へ反映する。

v1 は自宅 PC またはローカル端末で動作する単一ユーザー向け構成とする。

## 2. テクノロジースタック

| 領域 | 採用技術 |
| --- | --- |
| 言語 | Python 3.11 以上 |
| Slack 連携 | slack-bolt, Socket Mode |
| 設定 | JSON, python-dotenv, 環境変数 |
| 監査ログ | SQLite |
| AI 分類 | OpenAI Responses API |
| Excel 操作 | xlwings |
| テスト | unittest |
| パッケージ管理 | pyproject.toml, setuptools |

## 3. 実行構成

```mermaid
graph TD
    ENV[環境変数/.env.local] --> APP[tapinshift-agent]
    CFG[config.local.json] --> APP
    APP --> SLACK[Slack Socket Mode]
    APP --> DB[(SQLite)]
    APP --> EXCEL[Excelアプリ/xlwings]
    APP --> OPENAI[OpenAI API]
```

## 4. 実行環境

### 4.1 開発環境

- Linux devcontainer でも単体テストと設定診断は実行できる。
- 実 Excel 書き込みは Excel アプリが必要なため、Windows または macOS のローカル実機で検証する。
- Python 仮想環境は `.venv/` を使用する。

### 4.2 実運用環境

- Python 3.11 以上。
- Slack App の Socket Mode が利用できること。
- Excel アプリがインストールされていること。
- 勤務表 Excel ファイルへローカルファイルとしてアクセスできること。
- パスワード付き Excel を xlwings で開けること。

## 5. 設定仕様

設定ファイルは JSON 形式とし、既定パスは `config/config.local.json` とする。

主な設定項目:

| 項目 | 内容 |
| --- | --- |
| `timezone` | 打刻時刻のタイムゾーン |
| `database_path` | SQLite ファイルパス |
| `excel.path` | 勤務表 Excel ファイルパス |
| `excel.sheet_name` | 対象シート名 |
| `excel.columns` | Excel 列定義 |
| `excel.first_data_row` | データ開始行 |
| `excel.last_data_row` | データ終了行 |
| `excel.date_format` | 日付照合フォーマット |
| `excel.defaults` | 空セルに入れる既定値 |
| `time_rounding` | 時刻丸め設定 |
| `openai` | OpenAI モデルとしきい値 |
| `slack` | Slack token の環境変数名 |

## 6. 秘密情報

秘密情報は設定ファイルに直接保存しない。

| 環境変数 | 用途 |
| --- | --- |
| `SLACK_BOT_TOKEN` | Slack Bot Token |
| `SLACK_APP_TOKEN` | Slack App Token |
| `OPENAI_API_KEY` | OpenAI API Key |
| `TAPINSHIFT_EXCEL_PASSWORD` | Excel 開封パスワード |

`.env.local` を使う場合も Git 管理対象外にする。

## 7. モジュール境界

```mermaid
graph LR
    app[app.py] --> config[config.py]
    app --> slack[slack_app.py]
    app --> service[service.py]
    service --> classifier[classifier.py]
    service --> writer[excel_writer.py]
    service --> storage[storage.py]
    service --> rounding[time_rounding.py]
    storage --> models[models.py]
    classifier --> models
    writer --> models
```

### 境界ルール

- Slack 固有の payload 処理は `slack_app.py` に閉じる。
- 業務判断は `service.py` に集約する。
- Excel 操作は `excel_writer.py` に閉じる。
- SQLite 操作は `storage.py` に閉じる。
- OpenAI 呼び出しとローカル分類は `classifier.py` に閉じる。

## 8. 技術的制約

- v1 はローカル PC 起動中のみ処理する。
- Slack 操作をクラウドキューへ保存し、後から再処理する仕組みは持たない。
- xlwings は Excel アプリに依存するため、CI や devcontainer では実 Excel 書き込みを保証しない。
- Excel ファイルをユーザーが開いている場合、保存失敗や競合が発生する可能性がある。
- OpenAI API が未設定または利用できない場合、分類精度はローカルルール相当に下がる。

## 9. パフォーマンス要件

- 想定利用は単一ユーザーまたは小規模利用。
- 打刻 1 件ごとに Excel ファイルを開き、保存し、閉じる。
- 大量同時打刻や高頻度バッチ処理は対象外。
- Slack の ack は即時に返し、ユーザーには App Home 更新で結果を表示する。

## 10. 可用性・復旧

- Excel 反映に失敗しても打刻イベントは SQLite に保存する。
- 失敗内容は `error` として保存する。
- 手動編集で Excel を上書きして復旧する。
- v1 では自動リトライは実装しない。

## 11. セキュリティ要件

- token、API key、Excel password をログやドキュメントへ出力しない。
- `config.local.json`、`.env.local`、`data/` は Git 管理対象外にする。
- Slack ユーザー入力は文字列として受け取り、Excel 書き込み前に型変換する。
- 金額は整数に変換できる場合のみ Excel へ渡す。

## 12. 品質確認

### 基本コマンド

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/tapinshift-agent --config config/config.local.json --check-config
```

### 実機確認

```bash
.venv/bin/tapinshift-agent --config config/config.local.json
```

実機確認では Slack App Home 表示、出勤、退勤、日付編集、Excel 反映、失敗時ログ保存を確認する。
