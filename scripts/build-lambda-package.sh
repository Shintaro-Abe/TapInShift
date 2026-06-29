#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/lambda"
ZIP_PATH="${ROOT_DIR}/build/tapinshift-cloud.zip"

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}" "$(dirname "${ZIP_PATH}")"

cp -R "${ROOT_DIR}/src/tapinshift" "${BUILD_DIR}/tapinshift"

find "${BUILD_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${BUILD_DIR}" -type f -name "*.pyc" -delete

(
  cd "${BUILD_DIR}"
  zip -qr "${ZIP_PATH}" tapinshift
)

echo "${ZIP_PATH}"
