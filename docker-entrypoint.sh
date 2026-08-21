#!/bin/bash
set -e

# Restore latest data from Oracle Cloud Object Storage before starting the dashboard.
# This ensures the app always serves fresh data without manual intervention.
# The workflow uploads here daily; pulling on startup makes the app autonomous.

echo "[entrypoint] Restoring data from OCI..."
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force

echo "[entrypoint] Starting dashboard..."
exec streamlit run app.py
