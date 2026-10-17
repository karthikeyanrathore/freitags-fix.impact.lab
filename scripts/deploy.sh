#!/usr/bin/env bash
# Runs ON the VM (called by .github/workflows/deploy.yml over SSH, or by hand).
#   scripts/deploy.sh [git_ref]     default origin/main
# Pulls the latest main into the clone and rebuilds/restarts the compose stack.
# .env and the agent's fix/* branches are left untouched.
set -euo pipefail
cd "$(dirname "$0")/.."
REF="${1:-origin/main}"

echo "== $(hostname) · $(pwd)"
git fetch --quiet origin main
git checkout --quiet main
git merge --ff-only "$REF"
echo "== deploying $(git log -1 --format='%h %s')"
docker compose up -d --build --remove-orphans
docker compose ps

echo "== waiting for the gateway"
for i in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${SHOP_PORT:-8080}/api/state"; then echo "== up"; exit 0; fi
  sleep 2
done
docker compose logs --tail 50 shop agent order-api
echo "gateway did not come up"; exit 1
