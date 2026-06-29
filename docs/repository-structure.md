# TapInShift リポジトリ構造定義書

## 1. 目的

この文書は TapInShift のフォルダ構成、ファイル配置ルール、各ディレクトリの責務を定義する。

## 2. 全体構成

```text
TapInShift/
  AGENTS.md
  CLAUDE.md
  README.md
  README-CODEX-DEVCONTAINER.md
  pyproject.toml
  config/
  data/
  docs/
  knowledge/
  research/
  scripts/
  src/
    tapinshift/
  tests/
  .steering/
```

## 3. ルートファイル

| パス | 役割 |
| --- | --- |
| `README.md` | セットアップ、実行、概要 |
| `pyproject.toml` | Python パッケージ定義、依存関係、CLI エントリポイント |
| `AGENTS.md` | 開発プロセスとドキュメント管理ルール |
| `CLAUDE.md` | レビュー時の優先事項と出力ルール |
| `.gitignore` | ローカル秘密情報、仮想環境、生成物の除外 |
| `.gitattributes` | Git 属性設定 |

## 4. `docs/`

永続的ドキュメントを配置する。

| ファイル | 内容 |
| --- | --- |
| `docs/product-requirements.md` | プロダクト要求定義 |
| `docs/functional-design.md` | 機能設計 |
| `docs/architecture.md` | 技術仕様 |
| `docs/repository-structure.md` | リポジトリ構造 |
| `docs/development-guidelines.md` | 開発ガイドライン |
| `docs/glossary.md` | 用語定義 |

設計図やダイアグラムは関連する Markdown ファイル内に Mermaid または ASCII で記載する。

## 5. `knowledge/`

実装横断の運用ナレッジ、レビュー手順、調査から得た再利用可能な手順を配置する。アプリケーションの基本設計を定義する `docs/` とは分ける。

| ファイル | 内容 |
| --- | --- |
| `knowledge/codex-review-workflow.md` | Codex レビュー方式 |

## 6. `.steering/`

作業単位の要求、設計、タスクを配置する。

命名規則:

```text
.steering/YYYYMMDD-development-title/
  requirements.md
  design.md
  tasklist.md
```

新しい機能追加や修正では、新しい日付付きディレクトリを作る。

## 7. `src/tapinshift/`

アプリケーションコードを配置する。

| ファイル | 役割 |
| --- | --- |
| `__init__.py` | パッケージ初期化 |
| `app.py` | CLI エントリポイント、起動、設定診断 |
| `config.py` | JSON 設定読み込み、設定 dataclass |
| `models.py` | ドメインモデル、Enum |
| `slack_app.py` | Slack Bolt App、App Home、アクション、モーダル |
| `service.py` | 打刻・編集のアプリケーションサービス |
| `classifier.py` | ローカルルールによる任意メモ分類 |
| `excel_writer.py` | xlwings による Excel 書き込み |
| `storage.py` | SQLite 初期化、保存、取得 |
| `time_rounding.py` | 時刻丸め |
| `cloud/` | Lambda HTTP受付、DynamoDBキュー、Windows Agent同期処理 |

## 8. `tests/`

単体テストを配置する。

| ファイル | 対象 |
| --- | --- |
| `test_classifier.py` | ローカル分類 |
| `test_config.py` | 設定読み込み |
| `test_storage.py` | SQLite 保存・取得 |
| `test_time_rounding.py` | 時刻丸め |
| `test_service.py` | サービス層の接続 |
| `test_slack_app.py` | Slack App Home view 構造 |
| `test_cloud_*.py` | クラウド受付、DynamoDB変換、同期API、Windows Agent同期 |
| `test_dynamodb_store.py` | DynamoDBストアの条件付きclaimと設定保存 |

テストファイル名は `test_*.py` とする。

## 9. `config/`

設定ファイルを配置する。

| ファイル | 扱い |
| --- | --- |
| `config/config.example.json` | Git 管理対象。設定例 |
| `config/config.local.json` | Git 管理対象外。実環境設定 |

秘密情報は設定ファイルに直接書かず、環境変数名だけを書く。

## 10. `data/`

ローカルデータを配置する。Git 管理対象外。

| パス | 内容 |
| --- | --- |
| `data/tapinshift.sqlite3` | SQLite 監査ログ |
| `data/private/` | 実 Excel 勤務表などのローカルファイル |

勤務表や SQLite には個人情報や勤務情報が含まれるため、コミットしない。

## 11. `research/`

調査メモを配置する。

永続設計ではなく、技術選定や外部サービス調査の履歴として扱う。

## 12. `scripts/`

補助スクリプトを配置する。

現在はローカルセットアップ、設定確認、実機検証補助、ランブック HTML 生成、スキル導入に関するスクリプトを置く。

## 13. 生成物・除外対象

次は Git 管理対象外とする。

- `.venv/`
- `.venv-*/`
- `.env`, `.env.*`
- `config/config.local.json`
- `data/`
- `__pycache__/`
- `*.pyc`
- `*.egg-info/`
- 認証情報やローカルセッション情報

## 14. 配置ルール

- アプリケーション本体は `src/tapinshift/` に置く。
- テストは `tests/` に置き、対象モジュール名と対応させる。
- 永続ドキュメントは `docs/` に置く。
- 作業単位の一時ドキュメントは `.steering/` に置く。
- ローカル設定、Excel、SQLite、秘密情報は Git 管理対象にしない。
- 外部公開しない調査メモは `research/` に置く。
