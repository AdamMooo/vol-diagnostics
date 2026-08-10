#!/usr/bin/env bash
# Vol Diagnostics — prove the live site is running the code you pushed.
#
# Run this FROM YOUR OWN MACHINE, never on the server. That is the whole point:
# a deploy that gets killed mid-build cannot report its own failure (2026-08-06,
# backgrounded SSH died inside pip install), so the check has to be a separate
# process on a separate box that outlives it.
#
# Compares three SHAs and names which hop is stale:
#   origin/main  → what you pushed
#   server repo  → whether `git pull` landed
#   container    → whether `docker compose up --build` landed
#
# Usage: bash scripts/verify-deploy.sh
# Env:   VOL_SSH_KEY  (default ~/.ssh/vol-diagnostics.key)
#        VOL_HOST     (default ubuntu@40.233.113.63)
# Exit:  0 = live site is current, 1 = stale or unreachable

set -uo pipefail

KEY="${VOL_SSH_KEY:-$HOME/.ssh/vol-diagnostics.key}"
HOST="${VOL_HOST:-ubuntu@40.233.113.63}"

cd "$(dirname "$0")/.."

if [ ! -f "$KEY" ]; then
    echo "FAIL: no SSH key at $KEY (set VOL_SSH_KEY to override)"
    exit 1
fi

git fetch origin main --quiet || { echo "FAIL: cannot reach origin"; exit 1; }
EXPECTED="$(git rev-parse origin/main)"

REMOTE="$(ssh -i "$KEY" -o ConnectTimeout=10 "$HOST" '
    cd ~/vol-diagnostics 2>/dev/null || { echo "server=NOREPO"; echo "container=NOREPO"; exit 0; }
    echo "server=$(git rev-parse HEAD)"
    if [ "$(docker inspect -f "{{.State.Running}}" vol-diagnostics-dashboard 2>/dev/null)" != "true" ]; then
        echo "container=DOWN"
    else
        echo "container=$(docker compose exec -T dashboard printenv GIT_SHA 2>/dev/null || echo NOSTAMP)"
    fi
')" || { echo "FAIL: ssh to $HOST failed — cannot verify anything"; exit 1; }

SERVER="$(sed -n 's/^server=//p' <<<"$REMOTE" | tr -d '\r')"
CONTAINER="$(sed -n 's/^container=//p' <<<"$REMOTE" | tr -d '\r')"

short() { case "$1" in [0-9a-f]*) echo "${1:0:12}";; *) echo "$1";; esac; }

echo "origin/main   $(short "$EXPECTED")"
echo "server repo   $(short "$SERVER")"
echo "container     $(short "$CONTAINER")"
echo ""

case "$CONTAINER" in
    NOREPO)
        echo "FAIL: no ~/vol-diagnostics on $HOST — nothing is deployed from this repo."
        exit 1 ;;
    DOWN)
        echo "FAIL: dashboard container is not running. The site is down, not just stale."
        exit 1 ;;
    NOSTAMP|unknown)
        echo "STALE: container carries no GIT_SHA — it predates provenance stamping,"
        echo "       or was built without the build arg. Redeploy to establish a baseline."
        exit 1 ;;
esac

if [ "$SERVER" != "$EXPECTED" ]; then
    echo "STALE at the pull: server repo is not on origin/main."
    echo "       The deploy either never ran or the git pull failed."
    exit 1
fi

if [ "$CONTAINER" != "$SERVER" ]; then
    echo "STALE at the build: server repo is current but the site serves older code."
    echo "       The image build died and the old container came back up under its"
    echo "       restart policy. Re-run the deploy in the FOREGROUND and watch it."
    exit 1
fi

echo "OK — live site is running origin/main."
