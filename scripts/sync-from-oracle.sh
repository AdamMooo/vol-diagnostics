#!/usr/bin/env bash
# Vol Diagnostics — pull current out/ data down from Oracle to the local machine.
#
# Bash port of sync-from-oracle.ps1, for Linux/WSL dev boxes. Same semantics:
# Oracle's disk is the one source of truth (GitHub Actions writes to it daily
# via .github/workflows/daily-report.yml). One-way refresh for local dev only.
#
# Usage:
#   bash scripts/sync-from-oracle.sh
#   bash scripts/sync-from-oracle.sh --ip 1.2.3.4 --key ~/.ssh/other-key

set -euo pipefail

IP="40.233.113.63"
KEYFILE="$HOME/.ssh/vol-diagnostics.key"
REMOTE_USER="ubuntu"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ip)   IP="$2"; shift 2 ;;
        --key)  KEYFILE="$2"; shift 2 ;;
        --user) REMOTE_USER="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

LOCAL_OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/out"

if [[ ! -f "$KEYFILE" ]]; then
    echo "SSH key file not found: $KEYFILE" >&2
    exit 1
fi

# WSL note: a key copied off /mnt/c inherits 777 and ssh will refuse it outright.
perms=$(stat -c "%a" "$KEYFILE")
if [[ "$perms" != "600" && "$perms" != "400" ]]; then
    echo "SSH key perms are $perms — ssh requires 600. Fix with:" >&2
    echo "  chmod 600 $KEYFILE" >&2
    exit 1
fi

mkdir -p "$LOCAL_OUT"

echo "=== Vol Diagnostics — Sync FROM Oracle ==="
echo "Source: ${REMOTE_USER}@${IP}:~/vol-diagnostics/out/"
echo "Target: $LOCAL_OUT"
echo

# The dashboard container writes out/ as root (bind mount), so the ubuntu user
# can't read those files directly over scp — stage a chown'd copy first.
echo "[1/3] Staging a readable copy on the server..."
ssh -i "$KEYFILE" "${REMOTE_USER}@${IP}" \
    "sudo rm -rf /tmp/out_export && sudo cp -r ~/vol-diagnostics/out /tmp/out_export && sudo chown -R ${REMOTE_USER}:${REMOTE_USER} /tmp/out_export"

echo "[2/3] Copying down..."
scp -i "$KEYFILE" -r "${REMOTE_USER}@${IP}:/tmp/out_export/." "$LOCAL_OUT/"

echo "[3/3] Cleaning up server-side temp copy..."
ssh -i "$KEYFILE" "${REMOTE_USER}@${IP}" "sudo rm -rf /tmp/out_export"

echo
echo "=== Sync Complete ==="
