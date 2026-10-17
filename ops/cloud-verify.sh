#!/usr/bin/env bash
# Check that the deployed services send telemetry to Grafana Cloud: run one
# vulnerable-demo scan per service, then look for its traces, metrics, and
# logs through the stack's data source proxy.
#
# Reads GRAFANA_URL and GRAFANA_SA_TOKEN from .env (written by cloud-setup.sh).
# Prints no secret values.
# Usage: ops/cloud-verify.sh [app-url ...]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
: "${GRAFANA_URL:?run ops/cloud-setup.sh first}" "${GRAFANA_SA_TOKEN:?run ops/cloud-setup.sh first}"
apps=("$@"); [ $# -eq 0 ] && apps=(https://scanner-dev-4o95.onrender.com https://scanner-prod.onrender.com)

gf() { local p=$1; shift; curl -fsS -G -H "Authorization: Bearer $GRAFANA_SA_TOKEN" "$GRAFANA_URL/api/datasources/proxy/uid/$p" "$@"; }
ds=$(curl -fsS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" "$GRAFANA_URL/api/datasources")
uid() { jq -r --arg t "$1" '[.[] | select(.type == $t)] | (map(select(.name | startswith("grafanacloud-"))) + .) | .[0].uid' <<<"$ds"; }
prom=$(uid prometheus); loki=$(uid loki); tempo=$(uid tempo)

for app in "${apps[@]}"; do
  v=$(curl -s -m 120 "$app/api/health" | jq -r .version)
  id=$(curl -fsS -X POST "$app/api/scans" -H 'content-type: application/json' \
    -d '{"target":{"name":"cloud-verify","transport":"stdio","command":"vulnerable-demo"}}' | jq .id)
  echo "$app: version ${v:0:7}, scan $id submitted"
done

echo "Waiting 90 s for export (metrics export every 60 s by default)..."; sleep 90
start=$(( $(date +%s) - 900 ))

echo "== Traces (Tempo): scan.execute spans, last 15 min"
gf "$tempo/api/search" --data-urlencode 'q={ resource.service.name = "scanner-backend" && name = "scan.execute" }' \
  --data-urlencode "start=$start" --data-urlencode "end=$(date +%s)" --data-urlencode limit=10 \
  | jq -r '.traces[]? | "\(.traceID) \(.rootTraceName) \(.durationMs)ms"' | head -5

echo "== Metrics (Prometheus): scanner_scans_total by environment"
gf "$prom/api/v1/query" --data-urlencode 'query=sum by (deployment_environment, status) (scanner_scans_total)' \
  | jq -r '.data.result[]? | "\(.metric.deployment_environment // "?") \(.metric.status): \(.value[1])"'
gf "$prom/api/v1/query" --data-urlencode 'query=count(target_info{service_name="scanner-backend"}) by (deployment_environment)' \
  | jq -r '.data.result[]? | "target_info env=\(.metric.deployment_environment // "?")"'

echo "== Logs (Loki): scan log lines, last 15 min"
gf "$loki/loki/api/v1/query_range" --data-urlencode 'query={service_name="scanner-backend"} |= "scan"' \
  --data-urlencode "start=${start}000000000" --data-urlencode limit=5 \
  | jq -r '.data.result[]? | "\(.stream.deployment_environment // "?") trace=\(.stream.trace_id // "-") \(.values[0][1])"' | head -5
