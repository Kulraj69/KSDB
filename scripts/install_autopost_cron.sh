#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CRON_EXPR="${CRON_EXPR:-0 * * * *}"

AUTOP_CMD="cd \"$ROOT_DIR\" && $PYTHON_BIN scripts/auto_post.py >> automation/autopost.log 2>&1"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v "scripts/auto_post.py" > "$TMP_FILE" || true
printf "%s %s\n" "$CRON_EXPR" "$AUTOP_CMD" >> "$TMP_FILE"
crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "Installed cron schedule: $CRON_EXPR"
echo "Command: $AUTOP_CMD"
