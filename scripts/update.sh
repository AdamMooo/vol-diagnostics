#!/usr/bin/env bash
# Gamma OMM — Pull latest code and rebuild containers
# Run on the Oracle Cloud instance.
#
# Usage: bash scripts/update.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Vol Update ==="
echo ""

echo "[1/4] Pulling latest code..."
git pull
GIT_SHA="$(git rev-parse HEAD)"
export GIT_SHA
echo "      HEAD is ${GIT_SHA:0:12}"

echo "[2/4] Rebuilding containers..."
docker compose up -d --build

# `docker compose ps` saying "Up" proves nothing: under `restart: unless-stopped`
# a failed build leaves the OLD container running and reporting healthy. The only
# honest test is reading the commit back out of the container that is actually up.
echo "[3/4] Asserting the running container is that commit..."
RUNNING="$(docker compose exec -T dashboard printenv GIT_SHA | tr -d '\r')"
if [ "$RUNNING" != "$GIT_SHA" ]; then
    echo ""
    echo "  DEPLOY FAILED"
    echo "  container is running: ${RUNNING:-<no stamp>}"
    echo "  expected:             $GIT_SHA"
    echo ""
    echo "  The previous container is still serving stale code. The site will look"
    echo "  fine and be wrong. Re-run this script in the foreground and watch it."
    exit 1
fi
echo "      OK — ${GIT_SHA:0:12} is live"

# Deliberately non-fatal: stale `out/` data is a pipeline problem, not a bad
# deploy. It warns instead of failing so it can't block shipping code — but it
# no longer hides behind `|| true` either.
echo "[4/4] Data freshness..."
docker compose exec -T dashboard python -m engine.health_check \
    || echo "      WARN: health_check reports stale data — code deploy itself was fine"

echo ""
echo "=== Update Complete ==="
