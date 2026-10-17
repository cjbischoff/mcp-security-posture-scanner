#!/usr/bin/env bash
# Connect the Render services to Grafana Cloud, end to end, through the APIs:
#   1. find the Grafana Cloud stack and its OTLP gateway
#   2. create (or reuse) an access policy with metrics/logs/traces write
#   3. create a new OTLP token, test it, delete the previous one (= rotation)
#   4. merge the OTEL_* env vars into each Render service and redeploy it
#   5. create a stack service account token and push the dashboard + alert
#
# Reads from .env (gitignored): GRAFANA_CLOUD_TOKEN, RENDER_API_KEY,
# optional GRAFANA_STACK (slug; needed only if the token sees >1 stack).
# Writes back to .env: GRAFANA_URL, GRAFANA_SA_TOKEN, GRAFANA_OTLP_TOKEN_ID.
# Prints no secret values. Safe to run again.
#
# Usage: ops/cloud-setup.sh [render-service ...]   (default: scanner-dev scanner-prod)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo ".env not found" >&2; exit 1; }
set -a; . ./.env; set +a
: "${GRAFANA_CLOUD_TOKEN:?missing in .env}" "${RENDER_API_KEY:?missing in .env}"
services=("$@"); [ $# -eq 0 ] && services=(scanner-dev scanner-prod)
IMAGE=ghcr.io/cjbischoff/mcp-security-posture-scanner

gc() { curl -fsS -H "Authorization: Bearer $GRAFANA_CLOUD_TOKEN" -H "Content-Type: application/json" "$@"; }
rd() { curl -fsS -H "Authorization: Bearer $RENDER_API_KEY" -H "Content-Type: application/json" "$@"; }
save() {  # save KEY VALUE into .env (replace or append), value never printed
  local k=$1 v=$2; grep -v "^$k=" .env > .env.tmp || true; printf '%s=%s\n' "$k" "$v" >> .env.tmp; mv .env.tmp .env
}
step() { printf '\n== %s\n' "$*"; }

step "1. Grafana Cloud stack"
if [ -z "${GRAFANA_STACK:-}" ]; then
  stacks=$(gc "https://grafana.com/api/instances" | jq -r '.items[].slug')
  [ "$(wc -l <<<"$stacks" | tr -d ' ')" = 1 ] || { echo "Token sees several stacks; set GRAFANA_STACK in .env:"; echo "$stacks"; exit 1; }
  GRAFANA_STACK=$stacks
fi
stack=$(gc "https://grafana.com/api/instances/$GRAFANA_STACK")
stack_id=$(jq -r .id <<<"$stack"); url=$(jq -r .url <<<"$stack"); region=$(jq -r .regionSlug <<<"$stack")
otlp=$(gc "https://grafana.com/api/instances/$GRAFANA_STACK/connections" | jq -r .otlpHttpUrl)
echo "stack=$GRAFANA_STACK id=$stack_id region=$region url=$url otlp=$otlp"

step "2. Access policy scanner-otlp"
api="https://www.grafana.com/api/v1"
policy=$(gc "$api/accesspolicies?region=$region&name=scanner-otlp" | jq -r '.items[0].id // empty')
if [ -z "$policy" ]; then
  policy=$(gc -X POST "$api/accesspolicies?region=$region" -d "$(jq -n --arg s "$stack_id" \
    '{name:"scanner-otlp",displayName:"Scanner OTLP",scopes:["metrics:write","logs:write","traces:write"],realms:[{type:"stack",identifier:$s}]}')" | jq -r .id)
  echo "created policy $policy"
else
  echo "reusing policy $policy"
fi

step "3. New OTLP token, test, delete the previous one"
created=$(gc -X POST "$api/tokens?region=$region" -d "$(jq -n --arg p "$policy" --arg n "scanner-otlp-$(date +%Y%m%d%H%M%S)" '{accessPolicyId:$p,name:$n}')")
tok_id=$(jq -r .id <<<"$created"); tok=$(jq -r '.token // .key // empty' <<<"$created")
[ -n "$tok" ] || { echo "Token secret not found in response; fields: $(jq -c 'keys' <<<"$created")"; exit 1; }
user=""
for cand in "$stack_id" "$(jq -r '.htInstanceId // empty' <<<"$stack")"; do
  [ -n "$cand" ] || continue
  now=$(date +%s)000000000
  span=$(jq -n --arg t "$(openssl rand -hex 16)" --arg s "$(openssl rand -hex 8)" --arg n "$now" \
    '{resourceSpans:[{resource:{attributes:[{key:"service.name",value:{stringValue:"cloud-setup-test"}}]},
      scopeSpans:[{spans:[{traceId:$t,spanId:$s,name:"otlp-auth-test",kind:1,startTimeUnixNano:$n,endTimeUnixNano:$n}]}]}]}')
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "$cand:$tok" -H "Content-Type: application/json" \
    -X POST "$otlp/otlp/v1/traces" -d "$span")
  echo "OTLP test with instance id $cand: HTTP $code"
  [ "$code" = 200 ] && { user=$cand; break; }
done
[ -n "$user" ] || { echo "OTLP auth failed; new token $tok_id kept for inspection, Render unchanged" >&2; exit 1; }
if [ -n "${GRAFANA_OTLP_TOKEN_ID:-}" ] && [ "$GRAFANA_OTLP_TOKEN_ID" != "$tok_id" ]; then
  gc -X DELETE "$api/tokens/$GRAFANA_OTLP_TOKEN_ID?region=$region" >/dev/null && echo "deleted previous token $GRAFANA_OTLP_TOKEN_ID" || echo "previous token $GRAFANA_OTLP_TOKEN_ID not deleted (already gone?)"
fi
save GRAFANA_OTLP_TOKEN_ID "$tok_id"
header="Authorization=Basic%20$(printf '%s:%s' "$user" "$tok" | base64 | tr -d '\n')"

step "4. Render services"
for name in "${services[@]}"; do
  id=$(rd "https://api.render.com/v1/services?name=$name&limit=20" | jq -r --arg n "$name" '[.[].service | select(.name == $n)][0].id // empty')
  [ -n "$id" ] || { echo "$name: not found, skipped"; continue; }
  env=${name##*-}
  # PUT replaces the whole set: merge into the current vars so DATABASE_URL etc. stay
  current=$(rd "https://api.render.com/v1/services/$id/env-vars?limit=100" | jq '[.[].envVar | {key, value}]')
  merged=$(jq --arg e "$otlp/otlp" --arg h "$header" --arg env "$env" '
    map(select(.key | IN("OTEL_EXPORTER_OTLP_ENDPOINT","OTEL_EXPORTER_OTLP_HEADERS","OTEL_SERVICE_NAME","OTEL_RESOURCE_ATTRIBUTES") | not))
    + [{key:"OTEL_EXPORTER_OTLP_ENDPOINT",value:$e},{key:"OTEL_EXPORTER_OTLP_HEADERS",value:$h},
       {key:"OTEL_SERVICE_NAME",value:"scanner-backend"},{key:"OTEL_RESOURCE_ATTRIBUTES",value:("deployment.environment="+$env)}]' <<<"$current")
  rd -X PUT "https://api.render.com/v1/services/$id/env-vars" -d "$merged" >/dev/null
  echo "$name ($id): env vars set: $(jq -r '[.[].key] | join(",")' <<<"$merged")"
  # Env changes do not deploy by themselves. Redeploy the SHA that runs now;
  # a plain redeploy would run the service's original image tag (a rollback).
  svc_url=$(rd "https://api.render.com/v1/services/$id" | jq -r '.serviceDetails.url // empty')
  live=$(curl -s -m 90 "$svc_url/api/health" | jq -r '.version // empty')
  if [[ "$live" =~ ^[0-9a-f]{40}$ ]]; then
    rd -X POST "https://api.render.com/v1/services/$id/deploys" -d "$(jq -n --arg i "$IMAGE:$live" '{imageUrl:$i}')" >/dev/null
    echo "$name: redeploy started with $IMAGE:${live:0:7} ($svc_url)"
  else
    echo "$name: running version unknown ('$live'); NOT redeployed. Run: gh workflow run Deploy -f environment=$env -f tag=<sha>"
  fi
done

step "5. Dashboard and alert rule"
if [ -z "${GRAFANA_SA_TOKEN:-}" ] || ! curl -fsS -o /dev/null -H "Authorization: Bearer $GRAFANA_SA_TOKEN" "$url/api/folders"; then
  sa=$(gc -X POST "https://grafana.com/api/instances/$GRAFANA_STACK/api/serviceaccounts" -d '{"name":"scanner-provisioner","role":"Editor"}' 2>/dev/null | jq -r '.id // empty' || true)
  [ -n "$sa" ] || sa=$(gc "https://grafana.com/api/instances/$GRAFANA_STACK/api/serviceaccounts/search?query=scanner-provisioner" 2>/dev/null | jq -r '.serviceAccounts[0].id // empty' || true)
  [ -n "$sa" ] || { echo "Could not create a service account via the API. Create one by hand (Editor), put GRAFANA_SA_TOKEN=<token> in .env, and run this again."; exit 1; }
  sat=$(gc -X POST "https://grafana.com/api/instances/$GRAFANA_STACK/api/serviceaccounts/$sa/tokens" -d "{\"name\":\"push-$(date +%s)\"}" | jq -r .key)
  save GRAFANA_SA_TOKEN "$sat"; GRAFANA_SA_TOKEN=$sat
  echo "service account $sa: token saved to .env"
fi
save GRAFANA_URL "$url"
GRAFANA_URL=$url GRAFANA_SA_TOKEN=$GRAFANA_SA_TOKEN ops/grafana/push-to-cloud.sh

echo; echo "Done. Render redeploys take 1-3 minutes. Then: ops/cloud-verify.sh"
