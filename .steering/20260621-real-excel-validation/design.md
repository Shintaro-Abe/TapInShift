# 実 Excel 検証 設計

## 1. 方針

既存の v1 実装を前提に、実勤務表へ反映するための設定、検証手順、失敗時の確認観点を定義する。

基本設計の変更は行わない。今回の主目的は、`excel_writer.py` が実勤務表の構造に対して期待どおり動くことを実機で確認し、必要な最小修正を洗い出すことである。

## 2. 影響範囲

| 領域 | 対象 | 影響 |
| --- | --- | --- |
| 設定 | `config/config.local.json` | 実勤務表パス、シート、列、行範囲を設定する |
| Excel 書き込み | `src/tapinshift/excel_writer.py` | 実 Excel での開封、行探索、セル書き込みを確認する |
| 業務フロー | `src/tapinshift/service.py` | 成功、確認待ち、失敗時の状態保存を確認する |
| Slack UI | `src/tapinshift/slack_app.py` | App Home、ボタン、日付編集モーダルの実操作を確認する |
| 保存 | `src/tapinshift/storage.py` | 打刻イベントと手動編集履歴が保存されることを確認する |
| ドキュメント | `.steering/20260621-real-excel-validation/` | 検証意図とタスクを記録する |

## 3. 実行構成

```mermaid
flowchart TD
    U[ユーザー] --> SH[Slack App Home]
    SH --> B[Slack Bolt Socket Mode]
    B --> S[PunchService]
    S --> C[Classifier]
    S --> DB[(SQLite)]
    S --> W[ExcelTimesheetWriter]
    W --> X[実 Excel 勤務表]
```

## 4. 設定設計

`config/config.example.json` の既定マッピングは実勤務表向けの値を持っているため、実機では `config/config.local.json` に次を設定する。

| 設定 | 値 |
| --- | --- |
| `excel.path` | Git 管理対象外の実勤務表パス |
| `excel.sheet_name` | `6` |
| `excel.first_data_row` | `7` |
| `excel.last_data_row` | `37` |
| `excel.date_format` | `%Y-%m-%d` |
| `excel.columns.clock_in` | `F` |
| `excel.columns.clock_out` | `G` |
| `excel.columns.date` | `L` |
| `excel.columns.notice` | `W` |
| `excel.columns.expense_item` | `Y` |
| `excel.columns.amount` | `AB` |

秘密情報は設定ファイルへ書かず、環境変数で渡す。

検証時の `excel.path` は原本ではなく検証用コピーを指す。原本で確認する必要がある場合は、事前に復元可能なバックアップを作成してから実行する。

## 5. 書き込み設計

### 5.1 打刻

`ExcelTimesheetWriter.write_punch()` は次の順序で動く。

1. xlwings で Excel アプリを非表示起動する。
2. パスワード付き勤務表を開く。
3. シート `6` を取得する。
4. `L` 列から対象日を探す。
5. 既定値 `B=1`, `C=1`, `D=0`, `E=0` を空欄の場合のみ書く。
6. 出勤なら `F`、退勤なら `G` へ時刻を書く。
7. 分類結果がある場合は `W`, `Y`, `AB` へ書く。
8. 保存して閉じる。

打刻では既存の出勤・退勤セルを上書きしない。既存値がある場合は例外にし、サービス層で `failed` として保存する。

### 5.2 手動編集

`ExcelTimesheetWriter.update_day()` は対象日の `F`, `G`, `W`, `Y`, `AB` を上書きする。手動編集は復旧用途を兼ねるため、打刻と異なり既存値の上書きを許可する。

## 6. 検証設計

### 6.1 自動テスト

devcontainer では実 Excel アプリがないため、既存の unittest を品質確認として実行する。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

### 6.2 設定診断

実機では、仮想環境を作成してプロジェクトをインストールしてから次を実行する。

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Windows PowerShell の場合は次のように有効化する。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

その後、設定診断を実行する。

```bash
tapinshift-agent --config config/config.local.json --check-config
```

未設定の環境変数がある場合は `MISSING` が出てもよい。意図した不足だけが表示されることを確認する。

### 6.3 実機確認

実機確認では次を確認する。

| ケース | 期待結果 |
| --- | --- |
| App Home 表示 | 任意メモ、出勤、退勤、日付選択が表示される |
| 出勤 | 対象日の `F` 列へ時刻が入る |
| 退勤 | 対象日の `G` 列へ時刻が入る |
| メモ付き打刻 | 明確な分類結果だけ `W`, `Y`, `AB` へ反映される |
| 既存セル打刻 | 上書きせず `failed` として SQLite に残る |
| 手動編集 | `F`, `G`, `W`, `Y`, `AB` を上書きできる |
| 対象日なし | Excel を保存せず、失敗として SQLite に残る |

メモ分類の検証では、合否判断を固定するために入力例と期待値を記録してから実行する。OpenAI API を使う場合とローカルルールフォールバックを使う場合で結果が変わる可能性があるため、どちらのモードで検証したかも記録する。

## 7. リスクと対応

| リスク | 対応 |
| --- | --- |
| 実勤務表の日付セル形式が想定と違う | `_normalize_date()` の挙動を確認し、必要なら対応形式を追加する |
| Excel ファイルが開かれていて保存できない | 失敗として SQLite に保存し、手動復旧する |
| パスワード未設定 | `--check-config` で検知する |
| xlwings が実機に未導入 | 実機セットアップ手順で検知する |
| Slack token 権限不足 | App Home 表示とモーダル表示の時点で検知する |
| 原本の勤務表を壊す | 検証用コピーまたは事前バックアップを必須にする |

## 8. 永続ドキュメントへの影響

今回の作業は既存設計の実機検証であり、基本設計の変更はない。検証の結果、Excel 書き込み仕様や設定項目を変更する場合のみ `docs/` を更新する。
