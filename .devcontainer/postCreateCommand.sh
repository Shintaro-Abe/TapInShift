#!/usr/bin/env bash
set -euo pipefail

: "${CODEX_HOME:=/home/vscode/.codex}"
CLAUDE_HOME="/home/vscode/.claude"
GEMINI_HOME="/home/vscode/.gemini"

mkdir -p "${CODEX_HOME}"
sudo chown -R "$(id -u):$(id -g)" "${CODEX_HOME}"
mkdir -p "${CLAUDE_HOME}"
sudo chown -R "$(id -u):$(id -g)" "${CLAUDE_HOME}"
mkdir -p "${GEMINI_HOME}"
sudo chown -R "$(id -u):$(id -g)" "${GEMINI_HOME}"
sudo bash .devcontainer/install-claude-harness.sh

if [ ! -f "${CODEX_HOME}/config.toml" ]; then
  install -m 0600 .devcontainer/codex.config.toml "${CODEX_HOME}/config.toml"
fi

echo "Codex home: ${CODEX_HOME}"
codex --version
echo "Claude home: ${CLAUDE_HOME}"
claude --version
echo "Gemini home: ${GEMINI_HOME}"
gemini --version
