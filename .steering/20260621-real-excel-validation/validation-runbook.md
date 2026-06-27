# 実機検証ランブック

## 目的

Windows または macOS の実機で、TapInShift が Slack から Excel 勤務表へ反映できることを確認する。

この手順は、初めて触る人でも順番に確認できるように書いている。

---

## 0. 重要ルール

| ルール | 理由 |
| --- | --- |
| 原本の勤務表へ直接書き込まない | データ破損を防ぐため |
| 検証用コピーを使う | 失敗しても戻せるようにするため |
| パスワードや Slack token はファイルに書かない | 秘密情報の漏えいを防ぐため |
| `config.local.json`、Excel、SQLite は Git に入れない | 個人情報・秘密情報を守るため |

---

## 1. 事前に必要なもの

| 種類 | 必要なもの |
| --- | --- |
| PC | Windows または macOS |
| Excel | デスクトップ版 Excel |
| Python | Python 3.11 以上 |
| Slack | 検証用 Slack ワークスペース |
| Slack App | Socket Mode で動く Slack App |
| Excel ファイル | 検証用コピーの勤務表 |
| 秘密情報 | Excel パスワード、Slack bot token、Slack app token |

### 1.1 付属スクリプト

| ファイル | 用途 |
| --- | --- |
| `scripts/setup-local.sh` | macOS 用の Python 環境作成 |
| `scripts/setup-local.ps1` | Windows 用の Python 環境作成 |
| `scripts/check-local.sh` | macOS 用のテスト・設定チェック |
| `scripts/check-local.ps1` | Windows 用のテスト・設定チェック |
| `scripts/validate-local.sh` | macOS 用の実機検証一括実行 |
| `scripts/validate-local.ps1` | Windows 用の実機検証一括実行 |
| `scripts/timesheet_tools.py` | 検証用コピー作成、日付列確認、対象日検索、SQLite 確認 |
| `slack-app-manifest.example.yml` | Slack App 設定のひな形 |

---

## 2. Slack UI を使うための準備

Slack UI を使うには、Slack App の作成と設定が必要。

### 2.0 マニフェストで一括設定する（推奨）

Slack App の設定は、付属のマニフェストで一括投入できる。

1. Slack API の App 管理画面を開く。
2. `Create New App` を選ぶ。
3. `From an app manifest` を選ぶ。
4. 検証用 Slack ワークスペースを選ぶ。
5. `slack-app-manifest.example.yml` の内容を貼り付ける。
6. App を作成する。

これで Socket Mode、App Home、Interactivity、`app_home_opened`、scope が設定済みになる。  
残りは token の作成（2.2）とインストール（2.7）だけ行う。

手動で設定する場合は、以下 2.1 以降を順に行う。

### 2.1 Slack App を作成する

1. Slack API の App 管理画面を開く。
2. `Create New App` を選ぶ。
3. `From scratch` を選ぶ。
4. App 名を入力する。例: `TapInShift Local`
5. 検証用 Slack ワークスペースを選ぶ。
6. App を作成する。

### 2.2 Socket Mode を有効にする

1. 左メニューの `Socket Mode` を開く。
2. `Enable Socket Mode` をオンにする。
3. App-level token を作成する。
4. token 名を入力する。例: `tapinshift-socket`
5. scope に `connections:write` を追加する。
6. 作成された token を控える。

この token は `xapp-...` で始まる。  
この値を `SLACK_APP_TOKEN` として使う。

### 2.3 App Home を有効にする

1. 左メニューの `App Home` を開く。
2. `Home Tab` をオンにする。
3. 必要なら `Messages Tab` はオフのままでよい。

### 2.4 Interactivity を有効にする

1. 左メニューの `Interactivity & Shortcuts` を開く。
2. `Interactivity` をオンにする。
3. Socket Mode を使うため、公開 URL は不要。
4. 保存する。

### 2.5 Event Subscriptions を設定する

1. 左メニューの `Event Subscriptions` を開く。
2. `Enable Events` をオンにする。
3. `Subscribe to bot events` に次を追加する。

| Event | 用途 |
| --- | --- |
| `app_home_opened` | App Home を表示するため |

4. 保存する。

### 2.6 Bot token scope を設定する

左メニューの `OAuth & Permissions` を開く。  
`Bot Token Scopes` に次を追加する。

| Scope | 用途 |
| --- | --- |
| `chat:write` | Bot token を発行するための最小 scope として設定する |

App Home の表示とモーダル操作には、通常は追加 scope なしで足りる。  
権限不足のエラーが出た場合は、そのエラー文に従って scope を追加する。

### 2.7 App をワークスペースへインストールする

1. `OAuth & Permissions` を開く。
2. `Install to Workspace` を押す。
3. 許可する。
4. Bot User OAuth Token を控える。

この token は `xoxb-...` で始まる。  
この値を `SLACK_BOT_TOKEN` として使う。

### 2.8 Slack 側の確認

Slack クライアントで次を確認する。

- App 一覧に作成した App がある。
- App を開くと `ホーム` タブがある。
- まだ TapInShift を起動していない場合、画面が空でもよい。

---

## 3. Excel 検証用コピーを準備する

原本を直接使わず、検証用コピーを作る。

### 推奨: 3〜8 を一括実行する

次のスクリプトは、手順 3〜8 のうち機械的に実行できる作業をまとめて行う。

- 検証用コピー作成
- `.venv` 作成
- `pip install -e .`
- `pip install xlwings`
- 単体テスト
- `tapinshift-agent --check-config`
- Excel の日付列確認
- 必要な場合の `tapinshift-agent` 起動

秘密情報はファイルに保存しない。実行前に同じターミナルで環境変数として設定する。

### Windows PowerShell

```powershell
$env:TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
$env:SLACK_BOT_TOKEN="xoxb-..."
$env:SLACK_APP_TOKEN="xapp-..."

.\scripts\validate-local.ps1 -Source "<原本のパス>.xlsx"
```

チェック完了後、そのまま TapInShift を起動する場合:

```powershell
.\scripts\validate-local.ps1 -Source "<原本のパス>.xlsx" -StartAgent
```

`-StartAgent` を付けた場合、TapInShift は常駐する。  
PowerShell が「進行中」のままでも正常。Slack UI 検証が終わったら `Ctrl+C` で停止する。

検証用コピーを既に作成済みの場合:

```powershell
.\scripts\validate-local.ps1 -SkipCopy
```

検証用コピーを作り直す場合:

```powershell
.\scripts\validate-local.ps1 -Source "<原本のパス>.xlsx" -Force
```

`.venv\Scripts\Activate.ps1` が見つからないエラーが出る場合は、Windows 用ではない `.venv` が残っている。  
その場合は `.venv` を退避または削除してから再実行する。

```powershell
Rename-Item .venv .venv-linux-backup
.\scripts\validate-local.ps1 -Source "<原本のパス>.xlsx"
```

### macOS

```bash
export TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."

bash scripts/validate-local.sh --source "<原本のパス>.xlsx"
```

チェック完了後、そのまま TapInShift を起動する場合:

```bash
bash scripts/validate-local.sh --source "<原本のパス>.xlsx" --start-agent
```

`--start-agent` を付けた場合、TapInShift は常駐する。  
ターミナルが戻らなくても正常。Slack UI 検証が終わったら `Ctrl+C` で停止する。

検証用コピーを既に作成済みの場合:

```bash
bash scripts/validate-local.sh --skip-copy
```

検証用コピーを作り直す場合:

```bash
bash scripts/validate-local.sh --source "<原本のパス>.xlsx" --force
```

この一括実行が成功したら、手順 9 の Slack UI 検証へ進む。

### 個別に実行する場合: スクリプトでコピーを作る

`config/config.local.json` の `excel.path` をコピー先として使う。

### Windows PowerShell

```powershell
python scripts\timesheet_tools.py make-copy --source "<原本のパス>.xlsx"
```

### macOS

```bash
python3 scripts/timesheet_tools.py make-copy --source "<原本のパス>.xlsx"
```

コピー先が既にある場合は止まる。上書きする場合だけ `--force` を付ける。

```bash
python3 scripts/timesheet_tools.py make-copy --source "<原本のパス>.xlsx" --force
```

### 手動で作る場合

### Windows PowerShell

```powershell
Copy-Item "<原本のパス>.xlsx" "C:\TapInShiftData\private\202607_3373_勤務表.xlsx"
```

### macOS

```bash
cp "<原本のパス>.xlsx" "data/private/202607_3373_勤務表.xlsx"
```

その後、`config/config.local.json` の `excel.path` が検証用コピーを指していることを確認する。

例:

```json
"path": "C:\\TapInShiftData\\private\\202607_3373_勤務表.xlsx"
```

---

## 4. Python 環境を作る

手順 3 の一括実行を使った場合、この手順は完了済み。

リポジトリのルートで実行する。

### 推奨: スクリプトで作る

### Windows PowerShell

```powershell
.\scripts\setup-local.ps1
pip install xlwings
```

### macOS

```bash
bash scripts/setup-local.sh
pip install xlwings
```

`tapinshift-agent --help` が表示されれば成功。

### 手動で作る場合

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install xlwings
tapinshift-agent --help
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install xlwings
tapinshift-agent --help
```

---

## 5. 環境変数を設定する

手順 3 の一括実行を使う場合は、一括実行前にこの環境変数を設定する。

秘密情報はファイルに書かない。ターミナルに一時的に設定する。

### Windows PowerShell

```powershell
$env:TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
$env:SLACK_BOT_TOKEN="xoxb-..."
$env:SLACK_APP_TOKEN="xapp-..."
```

OpenAI 分類を使う場合だけ追加する。

```powershell
$env:OPENAI_API_KEY="sk-..."
```

### macOS

```bash
export TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
```

OpenAI 分類を使う場合だけ追加する。

```bash
export OPENAI_API_KEY="sk-..."
```

---

## 6. 設定チェックを行う

手順 3 の一括実行を使った場合、この手順は完了済み。

### 推奨: スクリプトで確認する

### Windows PowerShell

```powershell
.\scripts\check-local.ps1
```

### macOS

```bash
bash scripts/check-local.sh
```

### 手動で確認する場合

### Windows PowerShell

```powershell
python -m unittest discover -s tests
tapinshift-agent --config config/config.local.json --check-config
```

### macOS

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
tapinshift-agent --config config/config.local.json --check-config
```

期待する結果:

| 表示 | 意味 |
| --- | --- |
| `OK` | 問題なし |
| `MISSING` | 必須設定が不足 |
| `SKIP` | 任意設定が未設定 |

最低限、次が `OK` になること。

- Slack bot token
- Slack app token
- Excel file exists
- Excel password
- Database directory writable
- slack-bolt import
- xlwings import

OpenAI を使わない場合、OpenAI API key は `SKIP` でよい。

---

## 7. Excel の日付列を確認する

手順 3 の一括実行を使った場合、この手順は完了済み。

書き込み前に必ず確認する。

このプロジェクトは、`L` 列から対象日を探す。  
`L` 列の値が想定と違うと、Excel へ書き込めない。

次を実行する。

### Windows PowerShell

```powershell
python scripts\timesheet_tools.py inspect-dates
```

### macOS

```bash
python3 scripts/timesheet_tools.py inspect-dates
```

出力例:

```text
L7: datetime.datetime(2026, 6, 1, 0, 0)  [date]
L8: datetime.datetime(2026, 6, 2, 0, 0)  [date]
---
日付型: 31 件 / それ以外: 0 件
判定: すべて日付型。続行してよい。
```

手動で確認する場合は、Python を起動して次を貼り付ける。

```python
import os
import xlwings as xw

path = "C:/TapInShiftData/private/202607_3373_勤務表.xlsx"
password = os.environ["TAPINSHIFT_EXCEL_PASSWORD"]

app = xw.App(visible=False, add_book=False)
book = app.books.open(path, password=password)
sheet = book.sheets["6"]

for row in range(7, 38):
        print(row, repr(sheet.range(f"L{row}").value))

book.close()
app.quit()
```

確認結果:

| 出力例 | 判断 |
| --- | --- |
| `datetime.datetime(2026, 6, 1, 0, 0)` | 続行してよい |
| `1.0`、`1`、`'1'` | 日番号として続行できる |

`1.0` のような日番号でも、現在のコードは対象月の日付として扱える。

`2026-06-27` が見つからない場合は、`config/config.local.json` の `excel.path` が正しい勤務表を指しているかを先に確認する。

対象日の行だけ確認する場合は、次を実行する。

### Windows PowerShell

```powershell
python scripts\timesheet_tools.py find-date --date 2026-06-27
```

### macOS

```bash
python3 scripts/timesheet_tools.py find-date --date 2026-06-27
```

期待する結果:

```text
OK: 2026-06-27 は L33 に一致しました: 27.0 [day_number]
```

---

## 8. TapInShift を起動する

手順 3 の一括実行で `-StartAgent` または `--start-agent` を付けた場合、この手順は完了済み。

設定チェックが通ったら、TapInShift を起動する。

### Windows PowerShell

```powershell
tapinshift-agent --config config/config.local.json
```

### macOS

```bash
tapinshift-agent --config config/config.local.json
```

起動中はターミナルを閉じない。  
このターミナルが動いている間だけ Slack UI から反映できる。

---

## 9. Slack UI で確認する

Slack で作成した App を開く。  
`ホーム` タブを開く。

### 9.1 App Home 表示

確認すること:

- 任意メモ欄がある。
- `出勤` ボタンがある。
- `退勤` ボタンがある。
- `メモ反映` ボタンがある。
- 日付選択がある。
- 丸め単位選択がある。

### 9.1.1 丸め単位選択

1. `丸め単位` で `15分` などを選ぶ。
2. Slack に変更完了の表示が出る。
3. 以降の出勤・退勤で選んだ丸め単位が使われることを確認する。

注意:

- `丸めなし` を選ぶと、打刻時刻は分単位のまま反映される。
- 既定の丸め方向は、出勤が切り上げ、退勤が切り捨て。
- 選択した丸め単位は SQLite に保存され、エージェント再起動後も使われる。

### 9.2 出勤

1. 必要なら任意メモを入力する。
2. `出勤` を押す。
3. Slack に成功または失敗の表示が出る。
4. Excel の対象日の `F` 列に時刻が入ることを確認する。

期待:

- 時刻は `HH:MM` 相当。
- 秒は入らない。
- 既に値がある場合は上書きせず失敗する。

### 9.3 退勤

1. 必要なら任意メモを入力する。
2. `退勤` を押す。
3. Slack に成功または失敗の表示が出る。
4. Excel の対象日の `G` 列に時刻が入ることを確認する。

### 9.4 メモ付き打刻

次の例で確認する。

| 入力例 | 期待する反映 |
| --- | --- |
| `遅延証明あり` | `W` 列に反映 |
| `交通費320円` | `Y` 列に `交通費`、`AB` 列に `320` |

OpenAI API key を設定していない場合は、ローカルルールで分類する。

### 9.4.1 後から任意メモを反映する

出勤・退勤を先に押した後でも、任意メモだけを後から反映できる。

1. `表示・編集する日付` で対象日を選ぶ。
2. `任意メモ` に内容を入力する。
3. `メモ反映` を押す。
4. Slack に成功または失敗の表示が出る。
5. Excel の対象日の `W`、`Y`、`AB` 列に分類結果が反映されることを確認する。

注意:

- 出勤 `F`、退勤 `G` は変更しない。
- 分類できないメモは `needs_confirmation` または `failed` として SQLite に残る。

### 9.5 日付編集モーダル

1. 日付選択で対象日を選ぶ。
2. 編集モーダルが開くことを確認する。
3. 出勤、退勤、届出内容、経費内容、金額を入力する。
4. 保存する。
5. Excel に反映されることを確認する。

注意:

- 入力した項目だけ上書きする。
- 空欄の項目は既存値を保持する。
- セルを消したい場合は Excel で直接消す。

---

## 10. SQLite を確認する

SQLite には、成功や失敗の履歴が残る。

### 推奨: スクリプトで確認する

この方法は Python だけで確認できる。Windows に `sqlite3` コマンドが入っていなくてもよい。

### Windows PowerShell

```powershell
python scripts\timesheet_tools.py show-db --limit 5
```

実機検証で `config/config.local.json` の `database_path` を `C:\TapInShiftData\tapinshift.sqlite3` にしている場合も、上のコマンドで同じ設定を読み込む。

### macOS

```bash
python3 scripts/timesheet_tools.py show-db --limit 5
```

`show-db` は `punch_events`、`manual_edits`、表示許可された `app_settings` を表示する。現時点で表示する `app_settings` は `time_rounding.mode` のみ。

### 手動で確認する場合

`sqlite3` コマンドが使える環境だけで実行する。

```bash
sqlite3 data/tapinshift.sqlite3 "SELECT punch_type,status,error FROM punch_events ORDER BY rowid DESC LIMIT 5;"
sqlite3 data/tapinshift.sqlite3 "SELECT target_date,status,error FROM manual_edits ORDER BY id DESC LIMIT 5;"
sqlite3 data/tapinshift.sqlite3 "SELECT key,value FROM app_settings WHERE key='time_rounding.mode';"
```

Windows 実機で直接 SQLite を見る場合:

```powershell
sqlite3 "C:\TapInShiftData\tapinshift.sqlite3" "SELECT punch_type,status,error FROM punch_events ORDER BY rowid DESC LIMIT 5;"
sqlite3 "C:\TapInShiftData\tapinshift.sqlite3" "SELECT target_date,status,error FROM manual_edits ORDER BY id DESC LIMIT 5;"
sqlite3 "C:\TapInShiftData\tapinshift.sqlite3" "SELECT key,value FROM app_settings WHERE key='time_rounding.mode';"
```

確認すること:

| 状態 | 意味 |
| --- | --- |
| `reflected` | Excel へ反映済み |
| `needs_confirmation` | メモ確認待ち |
| `failed` | Excel 反映失敗 |

丸め単位を変更した場合は、`app_settings` に `time_rounding.mode` として `none`, `5m`, `10m`, `15m`, `20m`, `30m` のいずれかが保存される。

Excel password 環境変数が未設定の場合、アプリ本体の Excel writer は Excel を開く前にエラーで停止する。この失敗系は自動テストで確認する。

---

## 11. 失敗系を確認する

最低限、次を確認する。

| ケース | 期待 |
| --- | --- |
| 既に出勤セルに値がある日に出勤する | 上書きせず `failed` |
| 対象期間外の日付を編集する | `failed` |
| Excel パスワードを未設定にする | `failed` |

失敗しても、検証用コピーを使っていれば原本には影響しない。

---

## 12. 終了時の確認

最後に確認する。

- 検証用コピーで検証した。
- 原本へ直接書き込んでいない。
- 出勤、退勤、日付編集を確認した。
- 丸め単位選択と SQLite 保存を確認した。
- 失敗時に Slack と SQLite で確認できた。
- 秘密情報をファイルへ保存していない。
- コード修正をした場合はテストを実行した。

---

## 13. よくある問題

| 問題 | 対応 |
| --- | --- |
| Slack の Home が出ない | TapInShift が起動中か確認する。`app_home_opened` が設定済みか確認する |
| ボタンを押しても反応しない | Socket Mode と Interactivity が有効か確認する |
| `SLACK_BOT_TOKEN` が MISSING | `xoxb-...` の token を環境変数に設定する |
| `SLACK_APP_TOKEN` が MISSING | `xapp-...` の token を環境変数に設定する |
| Excel が開けない | パス、パスワード、Excel アプリの有無を確認する |
| 対象日が見つからない | 手順 7 の L 列形式を確認する |
| Excel に保存されない | 同じファイルを手動で開いていないか確認する |

---

## 14. 次回へ引き継ぐ内容

検証後、次を `handoff.md` または `tasklist.md` に記録する。

- 実行した OS
- Excel の L 列形式
- Slack App 設定で追加した scope
- 成功した操作
- 失敗した操作
- 修正が必要な箇所
- 実行したテスト結果
