#!/usr/bin/env bash
set -euo pipefail

WRAPPER_SOURCE=".devcontainer/claude-no-print-wrapper.sh"
CLAUDE_BIN="/usr/bin/claude"
REAL_CLAUDE="/usr/lib/claude-code/claude-real"

if [ ! -f "${WRAPPER_SOURCE}" ]; then
  echo "Claude harness wrapper not found: ${WRAPPER_SOURCE}" >&2
  exit 1
fi

if [ ! -e "${CLAUDE_BIN}" ] && [ ! -e "${REAL_CLAUDE}" ]; then
  echo "Claude Code binary not found: ${CLAUDE_BIN}" >&2
  exit 1
fi

install -d -m 0755 "$(dirname "${REAL_CLAUDE}")"

if [ -e "${CLAUDE_BIN}" ] && [ ! -e "${REAL_CLAUDE}" ]; then
  mv "${CLAUDE_BIN}" "${REAL_CLAUDE}"
fi

install -m 0755 "${WRAPPER_SOURCE}" "${CLAUDE_BIN}"
