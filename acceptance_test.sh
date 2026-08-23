#!/usr/bin/env bash
# Section 6 acceptance tests — run against a live dev server on :8000
# Not committed; a scratch verification harness.
set -u
BASE="http://127.0.0.1:8000/api"
PASS=0; FAIL=0
chk() { # chk "label" expected actual
  if [ "$2" = "$3" ]; then echo "  PASS  $1 (got $3)"; PASS=$((PASS+1));
  else echo "  FAIL  $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi
}
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "== 1. Visitor cannot write (no token) =="
chk "POST /posts/ -> 401" 401 "$(code -X POST $BASE/posts/ -H 'Content-Type: application/json' -d '{}')"
chk "PATCH /profile/ -> 401" 401 "$(code -X PATCH $BASE/profile/ -H 'Content-Type: application/json' -d '{}')"
chk "GET /dashboard/stats/ -> 401" 401 "$(code $BASE/dashboard/stats/)"

echo "== 2. No registration endpoint =="
chk "POST /auth/register/ -> 404" 404 "$(code -X POST $BASE/auth/register/ -H 'Content-Type: application/json' -d '{}')"

echo "== 3. Non-superuser cannot write (403) =="
VTOK=$(curl -s -X POST $BASE/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username":"visitor_user","password":"VisitorPass!2026"}' | ./venv/Scripts/python.exe -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
chk "login non-superuser returns token" "yes" "$([ -n "$VTOK" ] && echo yes || echo no)"
chk "POST /posts/ as non-superuser -> 403" 403 "$(code -X POST $BASE/posts/ -H "Authorization: Bearer $VTOK" -H 'Content-Type: application/json' -d '{}')"

echo "== 4. Owner CAN write =="
OTOK=$(curl -s -X POST $BASE/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username":"owner","password":"DevFolioDemo!2026"}' | ./venv/Scripts/python.exe -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
chk "owner login returns token" "yes" "$([ -n "$OTOK" ] && echo yes || echo no)"
chk "GET /auth/me/ as owner -> 200" 200 "$(code $BASE/auth/me/ -H "Authorization: Bearer $OTOK")"
chk "GET /dashboard/stats/ as owner -> 200" 200 "$(code $BASE/dashboard/stats/ -H "Authorization: Bearer $OTOK")"

echo "== 5. Drafts invisible to public, visible to owner =="
# find the draft slug via owner ?status=DRAFT
DRAFT_SLUG=$(curl -s "$BASE/posts/?status=DRAFT" -H "Authorization: Bearer $OTOK" | ./venv/Scripts/python.exe -c "import sys,json;r=json.load(sys.stdin);print(r['results'][0]['slug'] if r.get('results') else '')")
echo "  (draft slug: $DRAFT_SLUG)"
chk "public GET draft detail -> 404" 404 "$(code $BASE/posts/$DRAFT_SLUG/)"
chk "owner GET draft detail -> 200" 200 "$(code $BASE/posts/$DRAFT_SLUG/ -H "Authorization: Bearer $OTOK")"
PUB_COUNT=$(curl -s "$BASE/posts/" | ./venv/Scripts/python.exe -c "import sys,json;print(json.load(sys.stdin)['count'])")
chk "public post list excludes draft (count=4)" 4 "$PUB_COUNT"

echo "== 6. Unapproved comments hidden from public =="
PSLUG=$(curl -s "$BASE/posts/" | ./venv/Scripts/python.exe -c "import sys,json;print(json.load(sys.stdin)['results'][0]['slug'])")
# post #2 (RQ post) has the pending spam comment; check the second published post
RQSLUG=$(curl -s "$BASE/posts/" | ./venv/Scripts/python.exe -c "import sys,json;r=json.load(sys.stdin)['results'];print([p['slug'] for p in r if 'TanStack' in p['title']][0])")
PUBCOMMENTS=$(curl -s "$BASE/posts/$RQSLUG/comments/" | ./venv/Scripts/python.exe -c "import sys,json;d=json.load(sys.stdin);print(len(d if isinstance(d,list) else d.get('results',[])))")
echo "  (approved comments on RQ post: $PUBCOMMENTS — spam one should be hidden)"
chk "public comments exclude unapproved (1 approved)" 1 "$PUBCOMMENTS"

echo "== 7. Public comment create is held for moderation =="
NEWC=$(code -X POST $BASE/posts/$RQSLUG/comments/ -H 'Content-Type: application/json' -d '{"name":"Test Person","email":"t@example.com","content":"Great write-up, thanks for sharing this."}')
chk "POST comment -> 201" 201 "$NEWC"
PUBCOMMENTS2=$(curl -s "$BASE/posts/$RQSLUG/comments/" | ./venv/Scripts/python.exe -c "import sys,json;d=json.load(sys.stdin);print(len(d if isinstance(d,list) else d.get('results',[])))")
chk "new comment NOT shown publicly (still 1)" 1 "$PUBCOMMENTS2"

echo "== 8. Like toggle idempotent (visitor id) =="
VID="test-visitor-$(echo $RANDOM)"
L1=$(curl -s -X POST $BASE/posts/$PSLUG/like/ -H "X-Visitor-Id: $VID" | ./venv/Scripts/python.exe -c "import sys,json;d=json.load(sys.stdin);print(d.get('liked'),d.get('likes_count'))")
L2=$(curl -s -X POST $BASE/posts/$PSLUG/like/ -H "X-Visitor-Id: $VID" | ./venv/Scripts/python.exe -c "import sys,json;d=json.load(sys.stdin);print(d.get('liked'),d.get('likes_count'))")
echo "  (first like: [$L1]  second like: [$L2])"
chk "like without visitor id -> 400" 400 "$(code -X POST $BASE/posts/$PSLUG/like/)"

echo ""
echo "==================================="
echo "  RESULTS:  $PASS passed, $FAIL failed"
echo "==================================="
