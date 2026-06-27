#!/usr/bin/env bash
set -euo pipefail

REAL_CLAUDE="/usr/lib/claude-code/claude-real"

for arg in "$@"; do
  case "${arg}" in
    -p|--print|--print=*|-[!-]*p*)
      cat >&2 <<'EOF'
Blocked: non-interactive Claude Code execution is disabled in this dev container.

Use interactive Claude Code instead:
  claude

Do not use:
  claude -p
  claude --print
EOF
      exit 64
      ;;
  esac
done

if [ ! -t 1 ]; then
  case "${1:-}" in
    -v|--version|-h|--help)
      ;;
    *)
      cat >&2 <<'EOF'
Blocked: non-interactive Claude Code execution is disabled in this dev container.

Run Claude Code from an interactive terminal:
  claude
EOF
      exit 64
      ;;
  esac
fi

exec "${REAL_CLAUDE}" "$@"
