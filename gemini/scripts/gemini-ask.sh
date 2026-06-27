#!/usr/bin/env bash
set -euo pipefail

RAW_MODEL="${1:-flash}"
case "$RAW_MODEL" in
  flash) MODEL="gemini-2.5-flash" ;;
  pro)   MODEL="gemini-2.5-pro" ;;
  *)     MODEL="$RAW_MODEL" ;;
esac

if command -v gemini >/dev/null 2>&1; then
  GEMINI=(gemini)
else
  GEMINI=(npx --yes @google/gemini-cli)
fi

GEM_DIR="${HOME}/.gemini"
headless_auth=0
if [ -n "${GEMINI_API_KEY:-}" ] || [ -n "${GOOGLE_API_KEY:-}" ]; then headless_auth=1; fi
if [ "${GOOGLE_GENAI_USE_VERTEXAI:-}" = "true" ] && [ -n "${GOOGLE_CLOUD_PROJECT:-}" ] && [ -n "${GOOGLE_CLOUD_LOCATION:-}" ]; then headless_auth=1; fi

if [ "$headless_auth" -ne 1 ]; then
  cat >&2 <<'EOF'
[gemini-ask] 自動実行できるGemini headless認証が未設定です。
OAuthのみの場合、VS Code統合ターミナルで `gemini` を手動起動してください。
自動実行には GEMINI_API_KEY、GOOGLE_API_KEY、または Vertex AI 環境変数が必要です。
EOF
  exit 3
fi

PROMPT="$(cat)"
if [ -z "${PROMPT//[[:space:]]/}" ]; then
  echo "[gemini-ask] プロンプトが空です。" >&2
  exit 2
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

exec "${GEMINI[@]}" \
  --skip-trust \
  --approval-mode plan \
  -m "$MODEL" \
  -o text \
  --prompt "$PROMPT"
