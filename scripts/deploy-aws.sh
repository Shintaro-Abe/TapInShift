#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_BIN="${AWS_BIN:-aws}"
STACK_NAME="${STACK_NAME:-tapinshift-cloud}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-northeast-1}}"

if [[ -f "${ROOT_DIR}/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env.local"
  set +a
fi

required_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: ${name} is required." >&2
    exit 1
  fi
}

required_env SLACK_SIGNING_SECRET
required_env SLACK_BOT_TOKEN
required_env TAPINSHIFT_SYNC_TOKEN

ZIP_PATH="$("${ROOT_DIR}/scripts/build-lambda-package.sh")"

"${AWS_BIN}" cloudformation deploy \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/aws/cloudformation.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    SlackSigningSecret="${SLACK_SIGNING_SECRET}" \
    SlackBotToken="${SLACK_BOT_TOKEN}" \
    TapInShiftSyncToken="${TAPINSHIFT_SYNC_TOKEN}"

"${AWS_BIN}" lambda update-function-code \
  --region "${REGION}" \
  --function-name tapinshift-cloud \
  --zip-file "fileb://${ZIP_PATH}" >/dev/null

FUNCTION_URL="$("${AWS_BIN}" cloudformation describe-stacks \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" \
  --output text)"

echo "FunctionUrl=${FUNCTION_URL}"
echo "Slack Events URL=${FUNCTION_URL%/}/slack/events"
echo "Slack Interactivity URL=${FUNCTION_URL%/}/slack/actions"
