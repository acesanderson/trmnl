#!/usr/bin/env bash
# Deploy trmnl code changes to caruana.
#
# Usage:
#   bash scripts/deploy.sh
#
# Requires: GITHUB_PERSONAL_TOKEN env var (for git pull auth on caruana)

set -euo pipefail

LOCAL_REPO="$HOME/Brian_Code/trmnl-project"
REMOTE_REPO="/home/bianders/Brian_Code/trmnl-project"
GITHUB_REPO="acesanderson/trmnl"
HOST="caruana"
SERVICE="trmnl"
PORT=8070

echo "==> pushing to origin..."
git -C "$LOCAL_REPO" push

echo "==> [$HOST] pulling code..."
ssh "$HOST" "git -C $REMOTE_REPO pull --ff-only https://${GITHUB_PERSONAL_TOKEN}@github.com/${GITHUB_REPO}.git"

echo "==> [$HOST] syncing dependencies..."
ssh "$HOST" "cd $REMOTE_REPO && uv sync"

echo "==> [$HOST] restarting $SERVICE..."
ssh "$HOST" "sudo systemctl restart $SERVICE"

echo -n "==> [$HOST] waiting for $SERVICE on :$PORT ... "
for i in $(seq 1 20); do
    if ssh "$HOST" "curl -sf http://localhost:$PORT/ping" > /dev/null 2>&1; then
        echo "up"
        exit 0
    fi
    if [[ $i -eq 20 ]]; then
        echo "TIMEOUT after 20s"
        echo "    Run: ssh $HOST 'journalctl -u $SERVICE -n 30' for details"
        exit 1
    fi
    sleep 1
done
