#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/run_observations.log"

mkdir -p "$LOG_DIR"

# Clean up previous log
: > "$LOG_FILE"

echo "[wrapper] Logging to: $LOG_FILE"
echo "[wrapper] Command: python3 ${SCRIPT_DIR}/run_observations.py $*"

# Run + log to file and console
python3 "${SCRIPT_DIR}/run_observations.py" "$@" 2>&1 | tee -a "$LOG_FILE"

