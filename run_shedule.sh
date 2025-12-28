#!/usr/bin/env bash
set -euo pipefail

SCHEDULE_FILE="${1:-schedule.txt}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$SCHEDULE_FILE" ]]; then
  echo "Schedule file not found: $SCHEDULE_FILE" >&2
  exit 1
fi

echo "[runner] Using schedule: $SCHEDULE_FILE"
echo "[runner] Now: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo

while IFS= read -r line; do
  # Skip blanks/comments
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  # Parse: YYYY-MM-DD HH:MM  mode  runs  pause
  date_part="$(echo "$line" | awk '{print $1}')"
  time_part="$(echo "$line" | awk '{print $2}')"
  mode="$(echo "$line" | awk '{print $3}')"
  runs="$(echo "$line" | awk '{print $4}')"
  pause="$(echo "$line" | awk '{print $5}')"

  if [[ -z "${date_part:-}" || -z "${time_part:-}" || -z "${mode:-}" || -z "${runs:-}" || -z "${pause:-}" ]]; then
    echo "[runner] Skipping malformed line: $line" >&2
    continue
  fi

  target_str="${date_part} ${time_part}"
  target_epoch="$(date -d "$target_str" +%s 2>/dev/null || true)"
  now_epoch="$(date +%s)"

  if [[ -z "$target_epoch" ]]; then
    echo "[runner] Bad date/time: '$target_str' (line: $line)" >&2
    continue
  fi

  if (( target_epoch <= now_epoch )); then
    echo "[runner] Skipping past job at $target_str (line: $line)"
    continue
  fi

  wait_secs=$(( target_epoch - now_epoch ))
  echo "[runner] Next job: $target_str  mode=$mode runs=$runs pause=$pause (starts in ${wait_secs}s)"
  sleep "$wait_secs"

  echo "[runner] START $(date '+%Y-%m-%d %H:%M:%S %Z')  mode=$mode runs=$runs pause=$pause"
  "${SCRIPT_DIR}/observe.sh" --mode "$mode" --runs "$runs" --pause "$pause" || {
    echo "[runner] ERROR: job failed at $(date '+%Y-%m-%d %H:%M:%S %Z')"
    # Continue to next job rather than exiting
  }
  echo "[runner] END   $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo

done < "$SCHEDULE_FILE"

echo "[runner] All scheduled jobs completed."

