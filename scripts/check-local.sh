#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PYTHONPATH=src python3 -m unittest discover -s tests
tapinshift-agent --config config/config.local.json --check-config
