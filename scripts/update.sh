#!/usr/bin/env bash
# Gamma OMM — Pull latest code and rebuild containers
# Run on the Oracle Cloud instance.
#
# Usage: bash scripts/update.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Gamma OMM Update ==="
echo ""

echo "[1/3] Pulling latest code..."
git pull

echo "[2/3] Rebuilding containers..."
docker compose up -d --build

echo "[3/3] Verifying..."
docker compose ps
echo ""
docker compose exec dashboard python -m engine.health_check || true

echo ""
echo "=== Update Complete ==="
