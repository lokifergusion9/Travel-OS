#!/usr/bin/env bash
# Phase 0 smoke test: signup -> me -> complete onboarding, against a running API.
# Usage: bash scripts/smoke.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
EMAIL="owner-$RANDOM@example.com"

echo "→ Health"
curl -sf "$BASE/health" && echo

echo "→ Signup ($EMAIL)"
TOKENS=$(curl -sf -X POST "$BASE/api/v1/auth/signup" \
  -H 'Content-Type: application/json' \
  -d "{\"agency_name\":\"Himalaya Treks\",\"full_name\":\"Aadi\",\"email\":\"$EMAIL\",\"password\":\"supersecret123\"}")
ACCESS=$(echo "$TOKENS" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "  got access token: ${ACCESS:0:24}…"

echo "→ Me"
curl -sf "$BASE/api/v1/auth/me" -H "Authorization: Bearer $ACCESS" | python3 -m json.tool

echo "→ Complete onboarding"
curl -sf -X PATCH "$BASE/api/v1/auth/onboarding" \
  -H "Authorization: Bearer $ACCESS" -H 'Content-Type: application/json' \
  -d '{"completed":true}' | python3 -m json.tool

echo "✓ Smoke test passed"
