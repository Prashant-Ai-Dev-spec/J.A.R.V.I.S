#!/bin/bash
# Audit rotation script - run via cron
# Usage: ./scripts/rotate_audit.sh <ADMIN_API_KEY> [DAYS_TO_KEEP]

set -e

ADMIN_API_KEY="${1:-}"
DAYS_TO_KEEP="${2:-30}"
HOST="${JARVIS_HOST:-http://127.0.0.1:8000}"

if [ -z "$ADMIN_API_KEY" ]; then
    echo "Usage: $0 <ADMIN_API_KEY> [DAYS_TO_KEEP]"
    exit 1
fi

echo "[$(date)] Rotating audit logs - keeping last $DAYS_TO_KEEP days..."

curl -s -X POST "$HOST/admin/audit/rotate" \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"days\": $DAYS_TO_KEEP}" | jq .

echo "[$(date)] Audit rotation complete"
