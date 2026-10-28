#!/usr/bin/env bash
# Phase 1 smoke: signup -> stream itinerary -> approve -> stream creatives ->
# approval center decide. Usage: bash scripts/smoke_phase1.sh [BASE_URL]
set -euo pipefail
BASE="${1:-http://localhost:8090}"
EMAIL="trip-$RANDOM@example.com"
jget() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

echo "→ Signup"
ACCESS=$(curl -sf -X POST "$BASE/api/v1/auth/signup" -H 'Content-Type: application/json' \
  -d "{\"agency_name\":\"Trek Co\",\"full_name\":\"Aadi\",\"email\":\"$EMAIL\",\"password\":\"supersecret123\"}" \
  | jget "['access_token']")
AUTH="Authorization: Bearer $ACCESS"

echo "→ Generate itinerary (SSE)"
curl -sN -X POST "$BASE/api/v1/trips/generate" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"destination":"Spiti Valley","days":4,"audience":"college groups","budget_per_person":12000}' \
  > /tmp/trip_sse.txt
grep -o '"message": "[^"]*"' /tmp/trip_sse.txt | sed 's/"message": /   progress: /'
TRIP_ID=$(grep '"type": "trip_created"' /tmp/trip_sse.txt | head -1 | sed 's/^data: //' | jget "['trip_id']")
echo "   trip_id=$TRIP_ID"

echo "→ Get trip"
curl -sf "$BASE/api/v1/trips/$TRIP_ID" -H "$AUTH" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('   title:',d['title']);print('   status:',d['status']);print('   days:',len(d['days_plan']));print('   per_person:',(d.get('costing') or {}).get('per_person'))"

echo "→ Approve itinerary"
curl -sf -X POST "$BASE/api/v1/trips/$TRIP_ID/approve" -H "$AUTH" | jget "['status']" | sed 's/^/   trip status: /'

echo "→ Generate creatives (SSE)"
curl -sN -X POST "$BASE/api/v1/trips/$TRIP_ID/creatives/generate" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"kinds":["poster","caption","brochure"]}' \
  | grep -o '"kind": "[^"]*"' | sed 's/^/   asset: /' | sort -u

echo "→ Approval Center (pending)"
curl -sf "$BASE/api/v1/approvals?status=pending" -H "$AUTH" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('   pending approvals:',len(d));[print('    -',a['kind'],a['title']) for a in d]"

APPR_ID=$(curl -sf "$BASE/api/v1/approvals?status=pending" -H "$AUTH" | jget "[0]['id']")
echo "→ Decide first approval (approve)"
curl -sf -X POST "$BASE/api/v1/approvals/$APPR_ID/decide" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"decision":"approved"}' | jget "['status']" | sed 's/^/   approval status: /'

echo "✓ Phase 1 smoke passed"
