#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e .

echo "OK: Python 環境を作成しました"
echo "次に実機では必要に応じて実行してください: pip install xlwings"
echo "確認: tapinshift-agent --help"
