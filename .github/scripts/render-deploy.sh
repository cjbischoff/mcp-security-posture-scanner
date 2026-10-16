#!/usr/bin/env bash
# Deploy image $IMAGE:$TAG to a Render service through its deploy hook, then
# wait for $APP_URL/api/health to report the new version.
# Env: HOOK (deploy hook URL secret), IMAGE, TAG, APP_URL (optional).
set -euo pipefail

if [ -z "${HOOK:-}" ]; then
  echo "::warning::Deploy hook secret not set; skipping deploy."
  exit 0
fi

if ! [[ "$TAG" =~ ^[0-9a-f]{40}$ ]]; then echo "::error::TAG must be a full commit SHA"; exit 1; fi
image=$(echo "$IMAGE" | tr '[:upper:]' '[:lower:]'):$TAG
encoded=$(jq -rn --arg v "$image" '$v|@uri')
echo "Deploying $image"
curl -fsS -X POST "$HOOK&imgURL=$encoded" >/dev/null

if [ -z "${APP_URL:-}" ]; then
  echo "::warning::APP_URL not set; skipping health check."
  exit 0
fi

# Free instances can take about a minute to start
for _ in $(seq 1 40); do
  if curl -fsS "$APP_URL/api/health" | jq -e --arg t "$TAG" '.version == $t' >/dev/null 2>&1; then
    echo "Healthy at $APP_URL with version $TAG"
    exit 0
  fi
  sleep 15
done
echo "::error::$APP_URL did not report version $TAG within 10 minutes"
exit 1
