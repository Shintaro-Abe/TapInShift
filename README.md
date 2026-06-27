# TapInShift

SlackのApp Homeから出勤・退勤を記録し、自宅PCローカルのExcel勤務表へ反映するPythonローカルエージェントです。

## 採用構成

- Slack App Home + Socket Mode
- Pythonローカルエージェント
- SQLite監査ログ
- OpenAI APIによる任意メモ分類
- xlwingsによるローカルExcel書き込み

v1は自宅PCが起動中のみ処理します。クラウドキューや公開APIは使いません。

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
export SLACK_APP_TOKEN='xapp-...'
export OPENAI_API_KEY='sk-...'
export TAPINSHIFT_EXCEL_PASSWORD='...'
```

秘密情報はリポジトリに保存しません。`.env.local` を使う場合もGit管理対象外です。

## 実行

```bash
tapinshift-agent --config config/config.local.json
```

## Slack Appの前提

- Socket Modeを有効化する
- App Homeを有効化する
- Interactivityを有効化する
- `app_home_opened` イベントを購読する
- Bot token scopesはSlack App設定画面で最小権限から開始し、App Home表示・Modal表示に必要なものだけ追加する

## OpenAI分類

既定モデル:

- 通常: `gpt-5.4-nano`
- フォールバック: `gpt-5.4-mini`

任意メモが空欄の場合、OpenAI APIは呼びません。APIキーが未設定の場合は、正規表現・キーワードベースの簡易分類へフォールバックします。

## 編集

App Homeの日付選択から編集Modalを開きます。保存すると、設定ファイルの列定義に従って選択日の出勤・退勤・届出内容・経費内容・金額をExcelへ上書き反映します。

## 時刻丸め

v1既定は `none` です。タップ時刻をそのまま記録します。

将来対応用として、設定には次の値を想定しています。

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
