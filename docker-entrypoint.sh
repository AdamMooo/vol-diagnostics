#!/bin/bash
set -e

# Restore fresh data from OCI on every startup. Fail loudly if restore or validation fails —
# stale data is worse than no app. OCI credentials come from docker-compose env_file (.env).

echo "[entrypoint] Restoring data from OCI..."
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force 2>&1 \
  || {
    echo "[entrypoint] FATAL: OCI restore failed. Data may be stale or credentials invalid."
    echo "[entrypoint] Check: OCI_NAMESPACE, OCI_ACCESS_KEY_ID, network connectivity."
    exit 1
  }

echo "[entrypoint] Validating restored data freshness..."
python -m engine.health_check --strict 2>&1 \
  || {
    echo "[entrypoint] FATAL: Restored data failed freshness check (stale or incomplete)."
    echo "[entrypoint] Do not serve stale data to users."
    exit 1
  }

echo "[entrypoint] ✓ Fresh data restored and validated. Starting dashboard."
exec streamlit run app.py
