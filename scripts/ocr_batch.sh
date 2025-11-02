#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="${SCRIPT_DIR}/ocr_cli.py"
INPUT_DIR="${1:-/mnt/data/ocr_gen/in}"
OUTPUT_DIR="${2:-/mnt/data/ocr_gen/out}"
PROFILE="${OCR_PROFILE:-balanced}"
EXTRA_ARGS=()

# Collect optional arguments passed after positional parameters.
if [[ $# -gt 2 ]]; then
  shift 2
  EXTRA_ARGS=("$@")
fi

mkdir -p "${OUTPUT_DIR}"

for pdf in "${INPUT_DIR}"/*.pdf; do
  if [[ ! -e "${pdf}" ]]; then
    continue
  fi
  filename="$(basename "${pdf}")"
  output_path="${OUTPUT_DIR}/${filename}"
  python3 "${CLI_SCRIPT}" --profile "${PROFILE}" file "${pdf}" --output "${output_path}" "${EXTRA_ARGS[@]}"

done
