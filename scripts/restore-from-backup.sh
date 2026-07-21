#!/usr/bin/env bash
# Gamma OMM — Restore out/ from the Oracle Object Storage backup (BACKUP-02).
# Thin wrapper around the tested engine.restore_from_oci module — no boto3
# logic lives here.
#
# Safety: refuses to overwrite a populated --dest unless --force is passed.
# --dry-run lists what would be downloaded without writing anything to disk.
#
# Usage:
#   OCI_ACCESS_KEY_ID=... OCI_CUSTOMER_SECRET_KEY=... OCI_NAMESPACE=... \
#     ./scripts/restore-from-backup.sh --dry-run
#   OCI_ACCESS_KEY_ID=... OCI_CUSTOMER_SECRET_KEY=... OCI_NAMESPACE=... \
#     ./scripts/restore-from-backup.sh --force

set -euo pipefail

cd "$(dirname "$0")/.."

python -m engine.restore_from_oci "$@"
