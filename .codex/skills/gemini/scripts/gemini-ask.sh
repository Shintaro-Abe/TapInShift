#!/usr/bin/env bash
set -euo pipefail

TIMEOUT_SECONDS="${GEMINI_ASK_TIMEOUT_SECONDS:-1800}"

RAW_MODEL="${1:-flash}"
case "${RAW_MODEL}" in
  flash) MODEL="gemini-2.5-flash" ;;
  pro) MODEL="gemini-2.5-pro" ;;
  *) MODEL="${RAW_MODEL}" ;;
esac

if command -v gemini >/dev/null 2>&1; then
  GEMINI=(gemini)
elif command -v npx >/dev/null 2>&1; then
  GEMINI=(npx --yes @google/gemini-cli)
else
  cat >&2 <<'EOF'
[gemini-ask] Gemini CLI が見つかりません。
VS Code の統合ターミナルで Gemini CLI を利用できるようにしてください。
EOF
  exit 127
fi

GEM_DIR="${HOME}/.gemini"
authed=0
if [ -f "${GEM_DIR}/oauth_creds.json" ]; then
  authed=1
fi
if [ -f "${GEM_DIR}/settings.json" ] && grep -q 'selectedAuthType' "${GEM_DIR}/settings.json" 2>/dev/null; then
  authed=1
fi

if [ "${authed}" -ne 1 ]; then
  cat >&2 <<'EOF'
[gemini-ask] OAuth ログインが未設定です。
VS Code の統合ターミナルで `gemini` を対話起動し "Login with Google" でログインしてください。
ログイン後に再実行してください。
EOF
  exit 3
fi

PROMPT="$(cat)"
if [ -z "${PROMPT//[[:space:]]/}" ]; then
  echo "[gemini-ask] プロンプトが空です。" >&2
  exit 2
fi

WORKDIR="$(mktemp -d)"
STDOUT_FILE="${WORKDIR}/stdout.txt"
STDERR_FILE="${WORKDIR}/stderr.txt"
trap 'rm -rf "${WORKDIR}"' EXIT
cd "${WORKDIR}"

set +e
timeout "${TIMEOUT_SECONDS}" "${GEMINI[@]}" \
  --skip-trust \
  --approval-mode plan \
  -m "${MODEL}" \
  -o text \
  --prompt "${PROMPT}" \
  >"${STDOUT_FILE}" \
  2>"${STDERR_FILE}"
status=$?
set -e

if grep -Eqi 'Opening authentication page|Login with Google|Do you want to continue|認証|ログイン' "${STDOUT_FILE}" "${STDERR_FILE}"; then
  cat >&2 <<'EOF'
[gemini-ask] Gemini CLI が認証プロンプトを表示したため停止しました。

対処:
  1. VS Code統合ターミナルで `gemini` を対話起動し、OAuthログインを完了してください。
  2. Google Workspace / Code Assist / Developer Program 系アカウントの場合は、
     GOOGLE_CLOUD_PROJECT または GOOGLE_CLOUD_PROJECT_ID の設定が必要な場合があります。
  3. その後、再実行してください。
EOF
  cat "${STDERR_FILE}" >&2
  exit 3
fi

if [ "${status}" -eq 124 ]; then
  echo "[gemini-ask] Gemini CLI が ${TIMEOUT_SECONDS} 秒以内に完了しませんでした。" >&2
  cat "${STDERR_FILE}" >&2
  exit 124
fi

if [ "${status}" -ne 0 ]; then
  cat "${STDOUT_FILE}"
  cat "${STDERR_FILE}" >&2
  exit "${status}"
fi

cat "${STDOUT_FILE}"
