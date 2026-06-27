#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="config/config.local.json"
SOURCE=""
FORCE=0
SKIP_COPY=0
SKIP_INSTALL=0
START_AGENT=0
SHOW_DB=0
DB_LIMIT=5

usage() {
  cat <<'USAGE'
TapInShift 実機検証を一括実行する。

使い方:
  bash scripts/validate-local.sh --source "<原本のパス>.xlsx"

主なオプション:
  --source PATH     原本の勤務表パス。検証用コピー作成に使う
  --force           検証用コピーが既にある場合に上書きする
  --skip-copy       検証用コピー作成を省略する
  --config PATH     設定ファイル。既定: config/config.local.json
  --skip-install    pip install を省略する
  --start-agent     チェック完了後に tapinshift-agent を起動する
  --show-db         SQLite の最新履歴を表示する
  --db-limit N      --show-db の表示件数。既定: 5

事前に環境変数を設定する:
  export TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
  export SLACK_BOT_TOKEN="xoxb-..."
  export SLACK_APP_TOKEN="xapp-..."
USAGE
}

start_step() {
  echo
  echo "==> $1"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source)
      SOURCE="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --skip-copy)
      SKIP_COPY=1
      shift
      ;;
    --config)
      CONFIG="${2:-}"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --start-agent)
      START_AGENT=1
      shift
      ;;
    --show-db)
      SHOW_DB=1
      shift
      ;;
    --db-limit)
      DB_LIMIT="${2:-5}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: 不明なオプションです: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$SKIP_COPY" -eq 0 ] && [ -z "$SOURCE" ]; then
  echo "ERROR: --source を指定するか --skip-copy を付けてください。" >&2
  exit 2
fi

if [ ! -f "$CONFIG" ]; then
  echo "ERROR: 設定ファイルが見つかりません: $CONFIG" >&2
  echo "config/config.example.json から config/config.local.json を作成してください。" >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  start_step ".venv を作成"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ "$SKIP_INSTALL" -eq 0 ]; then
  start_step "Python 依存関係をインストール"
  python -m pip install -e .
  python -m pip install xlwings
fi

if [ "$SKIP_COPY" -eq 0 ]; then
  start_step "検証用コピーを作成"
  copy_args=(scripts/timesheet_tools.py make-copy --config "$CONFIG" --source "$SOURCE")
  if [ "$FORCE" -eq 1 ]; then
    copy_args+=(--force)
  fi
  python "${copy_args[@]}"
fi

start_step "単体テストを実行"
PYTHONPATH=src python -m unittest discover -s tests

start_step "設定チェックを実行"
tapinshift-agent --config "$CONFIG" --check-config

start_step "Excel の日付列を確認"
python scripts/timesheet_tools.py inspect-dates --config "$CONFIG"

if [ "$SHOW_DB" -eq 1 ]; then
  start_step "SQLite の最新履歴を表示"
  python scripts/timesheet_tools.py show-db --config "$CONFIG" --limit "$DB_LIMIT"
fi

if [ "$START_AGENT" -eq 1 ]; then
  start_step "tapinshift-agent を起動"
  echo "OK: チェック完了。tapinshift-agent を起動します。終了するまでこのターミナルを閉じないでください。"
  exec tapinshift-agent --config "$CONFIG"
fi

echo "OK: 自動チェックが完了しました。Slack UI 検証へ進んでください。"
