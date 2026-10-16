#!/usr/bin/env bash
# Push the scanner dashboard and the ScanFailureRateHigh alert rule to a
# Grafana instance (Grafana Cloud or the local LGTM) through its HTTP API.
# The local LGTM loads the same files by file provisioning; this script is
# for Grafana Cloud, where file provisioning is not available.
#
# Env:
#   GRAFANA_URL       e.g. https://<stack>.grafana.net
#   GRAFANA_SA_TOKEN  service account token with Editor role (or Admin)
# Usage: ops/grafana/push-to-cloud.sh
set -euo pipefail

dir=$(cd "$(dirname "$0")" && pwd)
: "${GRAFANA_URL:?set GRAFANA_URL}" "${GRAFANA_SA_TOKEN:?set GRAFANA_SA_TOKEN}"
api() { curl -fsS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" -H "Content-Type: application/json" "$@"; }

# Data source UIDs differ between stacks: find the first of each type,
# preferring Grafana Cloud's own (names start with "grafanacloud-").
ds=$(api "$GRAFANA_URL/api/datasources")
uid_for() {
  jq -r --arg t "$1" '[.[] | select(.type == $t)] | (map(select(.name | startswith("grafanacloud-"))) + .) | .[0].uid // empty' <<<"$ds"
}
prom=$(uid_for prometheus); loki=$(uid_for loki); tempo=$(uid_for tempo)
[ -n "$prom" ] || { echo "No Prometheus data source found" >&2; exit 1; }
echo "Data sources: prometheus=$prom loki=${loki:-none} tempo=${tempo:-none}"

# Folder "Scanner" (412/409 = already exists)
api -X POST "$GRAFANA_URL/api/folders" -d '{"uid":"scanner","title":"Scanner"}' >/dev/null 2>&1 || true

# Dashboard: swap the local data source UIDs for this stack's UIDs
jq --arg p "$prom" --arg l "${loki:-loki}" --arg t "${tempo:-tempo}" '
  walk(if type == "object" and has("uid") and has("type") then
         .uid = ({"prometheus": $p, "loki": $l, "tempo": $t}[.type] // .uid)
       else . end)
  | {dashboard: (. | del(.id)), folderUid: "scanner", overwrite: true}' \
  "$dir/scanner-dashboard.json" | api -X POST "$GRAFANA_URL/api/dashboards/db" -d @- >/dev/null
echo "Dashboard pushed: $GRAFANA_URL/d/scanner-scan-journey"

# Alert rule: convert the provisioning YAML rule to the API format
rule=$(uv run --quiet --no-project --with pyyaml python - "$dir/alerting.yaml" "$prom" <<'EOF'
import json, sys, yaml
group = yaml.safe_load(open(sys.argv[1]))["groups"][0]
rule = group["rules"][0]
for q in rule["data"]:
    if q["datasourceUid"] == "prometheus":
        q["datasourceUid"] = sys.argv[2]
rule.update(folderUID="scanner", ruleGroup=group["name"], orgID=1,
            noDataState=rule.get("noDataState", "OK"), execErrState=rule.get("execErrState", "Error"))
print(json.dumps(rule))
EOF
)
uid=$(jq -r .uid <<<"$rule")
if api "$GRAFANA_URL/api/v1/provisioning/alert-rules/$uid" >/dev/null 2>&1; then
  api -X PUT -H "X-Disable-Provenance: true" "$GRAFANA_URL/api/v1/provisioning/alert-rules/$uid" -d "$rule" >/dev/null
else
  api -X POST -H "X-Disable-Provenance: true" "$GRAFANA_URL/api/v1/provisioning/alert-rules" -d "$rule" >/dev/null
fi
interval=$(uv run --quiet --no-project --with pyyaml python -c "import yaml,sys,re; g=yaml.safe_load(open(sys.argv[1]))['groups'][0]; print(int(re.sub('s$','',g['interval'])))" "$dir/alerting.yaml")
api -X PUT -H "X-Disable-Provenance: true" "$GRAFANA_URL/api/v1/provisioning/folder/scanner/rule-groups/scanner-user-impact" \
  -d "$(api "$GRAFANA_URL/api/v1/provisioning/folder/scanner/rule-groups/scanner-user-impact" | jq --argjson i "$interval" '.interval = $i')" >/dev/null
echo "Alert rule pushed: $uid (routes to the stack's default notification policy)"
