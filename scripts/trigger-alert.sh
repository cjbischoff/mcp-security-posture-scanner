#!/usr/bin/env bash
# Fire ScanFailureRateHigh: turn on the scan-failure fault, then submit scans.
# Usage: scripts/trigger-alert.sh [N]   (default 12 scans)
#        scripts/trigger-alert.sh --off (turn the fault off again)
# Env: API (default http://127.0.0.1:8000), ADMIN_TOKEN (default: .env, else local-admin-token)
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091 # optional local overrides
[ -f .env ] && { set -a; . ./.env; set +a; }
API="${API:-http://127.0.0.1:8000}"
AUTH="Authorization: Bearer ${ADMIN_TOKEN:-local-admin-token}"

if [ "${1:-}" = "--off" ]; then
  curl -fsS -X DELETE -H "$AUTH" "$API/api/admin/faults/scan-failure"; echo
  exit 0
fi

N="${1:-12}"  # must outnumber recent good scans: the rule needs >50% failed over 5m
curl -fsS -X POST -H "$AUTH" "$API/api/admin/faults/scan-failure"; echo
for i in $(seq 1 "$N"); do
  curl -fsS -o /dev/null -w "scan $i/$N submitted: HTTP %{http_code}\n" \
    -X POST -H "Content-Type: application/json" "$API/api/scans" \
    -d '{"target":{"name":"vulnerable-demo","transport":"stdio","command":"vulnerable-demo"}}'
  sleep 2
done
echo "Fault is ON. Alert should fire within ~2 min. Turn off: $0 --off"
