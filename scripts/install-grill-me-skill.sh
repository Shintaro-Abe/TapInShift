#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity"
SKILLS=("grill-me" "grilling")

if ! command -v curl >/dev/null 2>&1; then
  echo "[install-grill-me] ERROR: curl is required." >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

for skill_name in "${SKILLS[@]}"; do
  source_url="${BASE_URL}/${skill_name}/SKILL.md"
  dest_dir=".codex/skills/${skill_name}"
  dest_file="${dest_dir}/SKILL.md"

  mkdir -p "$dest_dir"
  curl -fsSL "$source_url" -o "$tmp_file"

  if ! grep -q "name: ${skill_name}" "$tmp_file"; then
    echo "[install-grill-me] ERROR: downloaded file does not look like ${skill_name} SKILL.md" >&2
    exit 1
  fi

  install -m 0644 "$tmp_file" "$dest_file"

  echo "[install-grill-me] Installed: $dest_file"
  echo "[install-grill-me] Source: $source_url"
done
