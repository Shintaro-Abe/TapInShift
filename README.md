# TapInShift

SlackのApp Homeから出勤・退勤を記録し、ローカルExcel勤務表へ反映する勤怠入力ツールです。

外出中などWindows端末が停止している場合は、AWS Lambda Function URL + DynamoDB のクラウドキューでSlack操作を受け付け、Windows Agent起動後に未同期イベントをExcelへ反映します。

## 採用構成

- Slack App Home + HTTP Request URL
- AWS Lambda Function URL + DynamoDB
- Windows同期エージェント
- SQLite監査ログ
- ローカルルールによる任意メモ分類
- xlwingsによるローカルExcel書き込み

ExcelファイルとExcelパスワードはクラウドに置きません。クラウド側には打刻、メモ、編集、同期状態に必要な最小限のデータだけを保存します。

## セットアップ

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
cp config/config.example.json config/config.local.json
```

`config/config.local.json` に勤務表パス、シート名、列設定を記入します。

必要な環境変数:

```bash
export SLACK_BOT_TOKEN='xoxb-...'
export TAPINSHIFT_EXCEL_PASSWORD='...'
export TAPINSHIFT_CLOUD_ENDPOINT='https://<lambda-function-url>'
export TAPINSHIFT_SYNC_TOKEN='...'
```

秘密情報はリポジトリに保存しません。`.env.local` を使う場合もGit管理対象外です。

Windows PowerShellで `.env.local` を読み込む場合:

```powershell
.\scripts\load-env-local.ps1
$env:TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
```

`--sync-now` や `--poll-cloud` で `HTTP Error 401: Unauthorized` が出る場合は、Windows側の `TAPINSHIFT_SYNC_TOKEN` とAWS側の同期tokenが一致していません。`.env.local` を読み込み直してから再実行します。

Windowsログオン時にクラウド同期Agentを自動起動する場合は、`.env.local` に `TAPINSHIFT_EXCEL_PASSWORD` も保存したうえで、次を実行します。

```powershell
.\scripts\register-cloud-agent-task.bat
```

`アクセスが拒否されました` で失敗する場合は、管理者としてPowerShellを開き直して再実行するか、管理者権限不要のStartupフォルダ登録を使います。

```powershell
.\scripts\register-cloud-agent-startup.bat
```

タスクスケジューラ方式で登録後すぐ起動する場合:

```powershell
schtasks /Run /TN "TapInShift Cloud Agent"
```

Startupフォルダ方式で登録後すぐ起動する場合:

```powershell
.\scripts\start-cloud-agent.bat
```

自動起動される処理は `scripts/start-cloud-agent.bat` です。

## 実行

```bash
tapinshift-agent --config config/config.local.json
```

クラウドキューから未同期イベントを1回だけ同期する場合:

```bash
tapinshift-agent --config config/config.local.json --sync-now
```

起動中に5分ごとに同期する場合:

```bash
tapinshift-agent --config config/config.local.json --poll-cloud
```

## Slack Appの前提

- Socket Modeは無効化する
- App Homeを有効化する
- Interactivityを有効化する
- `app_home_opened` イベントを購読する
- Event Subscriptions Request URLを `<Lambda Function URL>/slack/events` にする
- Interactivity Request URLを `<Lambda Function URL>/slack/actions` にする
- Bot token scopesはSlack App設定画面で最小権限から開始し、App Home表示・Modal表示に必要なものだけ追加する

## 任意メモ分類

任意メモはローカルルールで分類します。届出内容は拠点・建物名・駅名などの場所情報、経費内容は金額に対応する内容として扱います。交通費の場合、経費内容には経路のみを入れます。
出勤・退勤ボタンでは任意メモ欄を送信せず、メモは `メモ反映` ボタンで対象日に反映します。

## 編集

App Homeの日付選択から編集Modalを開きます。保存すると、設定ファイルの列定義に従って選択日の出勤・退勤・届出内容・経費内容・金額をExcelへ上書き反映します。

## 時刻丸め

既定は `none` です。タップ時刻をそのまま記録します。

Slack App Homeから次の丸め単位を選択できます。

- `5m`
- `10m`
- `15m`
- `20m`
- `30m`

丸め方向は `nearest`、`floor`、`ceil` を想定しています。

## テスト

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
