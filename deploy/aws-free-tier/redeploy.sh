#!/usr/bin/env bash
# Push local code to the live demo box and rebuild. Run from your Mac:
#   bash deploy/aws-free-tier/redeploy.sh <PUBLIC_IP>
#   (or: DEPLOY_HOST=<ip> bash deploy/aws-free-tier/redeploy.sh)
#
# Docker layer cache makes code-only changes rebuild in ~1-2 min.
set -euo pipefail

HOST="${1:-${DEPLOY_HOST:-}}"
KEY="${DEPLOY_KEY:-$HOME/.ssh/travelos-demo.pem}"
if [ -z "$HOST" ]; then
  echo "Usage: bash deploy/aws-free-tier/redeploy.sh <PUBLIC_IP>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSHOPTS="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "→ syncing code to $HOST"
rsync -az -e "ssh $SSHOPTS" \
  --exclude '.git' --exclude 'node_modules' --exclude 'dist' --exclude '.venv' \
  --exclude '__pycache__' --exclude '*.pyc' --exclude 'deploy/aws-free-tier/.env' \
  --exclude 'backend/storage' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '.vite' \
  "$ROOT/" "ec2-user@$HOST:/home/ec2-user/TravelOS/"

echo "→ rebuilding + restarting on $HOST"
ssh $SSHOPTS "ec2-user@$HOST" \
  "cd ~/TravelOS/deploy/aws-free-tier && sudo docker compose up -d --build"

echo "✓ redeployed → http://$HOST"
