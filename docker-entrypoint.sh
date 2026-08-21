#!/bin/bash
# Don't fail on restore errors — the app starts regardless so it's always available.
# OCI is the source of truth, but graceful degradation (stale data > no data) ensures
# robustness if credentials or connectivity are unavailable on startup.
#
# OCI credentials come from docker-compose env_file (.env), which sets them in the
# container's environment. The restore command reads them as standard env vars.

echo "[entrypoint] Attempting to restore fresh data from OCI..."
if python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force 2>&1; then
  echo "[entrypoint] ✓ Restored from OCI successfully."
else
  echo "[entrypoint] ⚠ OCI restore failed (credentials/network/empty bucket); starting with local data."
fi

echo "[entrypoint] Starting dashboard..."
exec streamlit run app.py
