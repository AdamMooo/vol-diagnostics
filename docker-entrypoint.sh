#!/bin/bash
set -e

# Restore latest data from Oracle Cloud Object Storage before starting the dashboard.
# This ensures the app always serves fresh data without manual intervention.
# The workflow uploads here daily; pulling on startup makes the app autonomous.

# Load OCI credentials from .env (docker-compose passes via env_file, but the
# shell may not inherit them; explicit load ensures the restore has what it needs)
if [ -f /app/.env ]; then
  set -a
  source /app/.env
  set +a
fi

echo "[entrypoint] Restoring data from OCI..."
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force

echo "[entrypoint] Starting dashboard..."
exec streamlit run app.py
