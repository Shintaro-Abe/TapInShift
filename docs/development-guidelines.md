# TapInShift 開発ガイドライン

## 1. 目的

この文書は TapInShift の開発、テスト、設定、Git、セキュリティに関する標準ルールを定義する。

## 2. 基本方針

- 既存の Excel 勤務表運用を壊さない。
- Slack UI、業務ロジック、Excel 書き込み、SQLite 保存を分離する。
- 失敗時も入力内容とエラーを SQLite に残す。
- 秘密情報や勤務表データを Git に含めない。
- 小さな変更でも関連テストを実行する。

## 3. Python コーディング規約

- Python 3.11 以上を対象にする。
- 型ヒントを付ける。
- dataclass は設定値や値オブジェクトに使う。
- Enum は状態や種別の固定値に使う。
- 副作用のある処理は境界モジュールに寄せる。
- 広い例外捕捉は、失敗を監査ログへ残す目的に限定する。

## 4. モジュール責務

| モジュール | 責務 |
| --- | --- |
| `app.py` | 起動、設定診断、依存構築 |
| `config.py` | 設定読み込み |
| `slack_app.py` | Slack payload と Block Kit |
| `service.py` | 業務フロー統合 |
| `classifier.py` | メモ分類 |
| `excel_writer.py` | Excel 操作 |
| `storage.py` | SQLite 操作 |
| `time_rounding.py` | 時刻丸め |

## 5. 命名規則

- クラス名は `PascalCase`。
- 関数、変数、モジュールは `snake_case`。
- Enum 値は既存に合わせて小文字文字列にする。
- Slack action ID は `tapinshift_` 接頭辞を付ける。
- 環境変数は大文字スネークケースにする。

## 6. 設定ルール

- 設定例は `config/config.example.json` に置く。
- 実環境設定は `config/config.local.json` に置き、Git 管理しない。
- token、API key、Excel password は環境変数で渡す。
- ローカル実行時は `.env.local` を使ってよいが、Git 管理しない。

## 7. Slack 実装ルール

- Slack payload の解釈は `slack_app.py` に閉じる。
- アクションは必ず `ack()` する。
- App Home の状態表示はユーザーが次に取る行動を判断できる文言にする。
- Slack UI の変更時は `tests/test_slack_app.py` で構造を固定する。

## 8. Excel 実装ルール

- Excel 操作は `excel_writer.py` に閉じる。
- 打刻時は既存の出勤・退勤セルを上書きしない。
- 手動編集時のみ上書きを許可する。
- Excel の列、行範囲、日付形式は設定ファイルから取得する。
- Excel 書き込み失敗は握りつぶさず、サービス層で failed として保存する。

## 9. SQLite 実装ルール

- スキーマ変更は `EventStore.initialize()` に反映する。
- 打刻イベントは `slack_event_id` を主キーにする。
- 手動編集は追記履歴として保存する。
- エラー文字列は復旧判断に必要な範囲で保存する。

## 10. OpenAI 分類ルール

- 空メモでは OpenAI API を呼ばない。
- API キー未設定時はローカルルール分類へフォールバックする。
- 分類が曖昧な場合は Excel へ反映せず確認待ちにする。
- 分類結果は `Classification` に正規化してから扱う。

## 11. テスト規約

### 実行コマンド

```bash
.venv/bin/python -m unittest discover -s tests
```

仮想環境がない場合:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

### テスト対象

- 分類ロジック。
- 時刻丸め。
- SQLite 保存・取得。
- サービス層の成功、確認待ち、失敗。
- Slack view 構造。

### 実 Excel テスト

- devcontainer では実 Excel 書き込みを必須にしない。
- Windows または macOS の Excel アプリがある実機で手動確認する。

## 12. 品質チェック

変更後は次を確認する。

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/tapinshift-agent --config config/config.local.json --check-config
```

`--check-config` は環境変数未設定の場合に失敗してよい。失敗内容が期待どおりか確認する。

## 13. Git ルール

- 関係ない変更を混ぜない。
- `.venv/`, `.env.local`, `config/config.local.json`, `data/` をコミットしない。
- 実 Excel 勤務表、SQLite、token、API key、パスワードをコミットしない。
- 生成された `__pycache__/` や `*.pyc` をコミットしない。

## 14. ドキュメント更新ルール

- 基本設計や方針が変わる場合は `docs/` を更新する。
- 作業単位の意図やタスクは `.steering/` に記録する。
- 図表は関連する Markdown 内に直接書く。
- コードとドキュメントの不一致を残さない。

## 15. セキュリティルール

- 秘密情報をログ、テスト、ドキュメント、コミットに含めない。
- Slack token、OpenAI API key、Excel password は環境変数で管理する。
- ユーザー入力は Excel 書き込み前に正規化する。
- 金額は整数に変換できる場合のみ反映する。
- 失敗時のエラーに秘密情報が含まれないよう注意する。

