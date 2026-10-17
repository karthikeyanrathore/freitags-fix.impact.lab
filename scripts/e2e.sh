#!/usr/bin/env bash
# End-to-end self-healing test against a running stack.
#   scripts/e2e.sh [base_url]      default http://127.0.0.1:8080
# Checks: shop + admin load, an order works, a 429 vendor outage triggers the agent,
# the agent commits and deploys a fix, and the health check passes with the outage still on.
set -euo pipefail
B="${1:-http://127.0.0.1:8080}"
TIMEOUT="${E2E_TIMEOUT:-150}"
json() { python3 -c "import json,sys; s=json.load(sys.stdin); $1"; }
post() { local d="${2:-}"; [ -n "$d" ] || d='{}'; curl -fsS -X POST "$B$1" -H 'Content-Type: application/json' -d "$d"; }
fail() { echo "FAIL: $*"; exit 1; }

echo "== waiting for $B"
for i in $(seq 1 60); do curl -fsS -o /dev/null "$B/api/state" && break; sleep 2; [ "$i" = 60 ] && fail "stack not up"; done

echo "== pages"
for p in / /admin /admin/ /cart-client.js; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$B$p"); [ "$code" = 200 ] || fail "$p returned $code"; echo "   $p 200"
done

echo "== reset + healthy order"
post /api/admin/reset >/dev/null
post /api/admin/autopilot '{"on": true}' >/dev/null
post /api/admin/monitor '{"on": true}' >/dev/null
post /api/cart/add '{"cartId":"e2e","itemId":"1"}' | json "assert s['count']==1, s; print('   add ok')"
post /api/admin/check | json "assert s['ok'], s; print('   health check ok (5/5)')"

echo "== vendor outage: 429"
post /api/admin/fault '{"mode":"429"}' | json "assert s['fault']=='429'; print('   fault on')"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$B/api/cart/add" -H 'Content-Type: application/json' -d '{"cartId":"e2e","itemId":"2"}')
[ "$code" = 429 ] || fail "expected 429 from the vendor, got $code"; echo "   customer request fails with 429"

echo "== waiting for the agent (up to ${TIMEOUT}s)"
deadline=$((SECONDS + TIMEOUT)); status=none
while [ $SECONDS -lt $deadline ]; do
  status=$(curl -fsS "$B/api/state" | json "r=s['runs']; print(r[-1]['status'] if r else 'none')")
  case "$status" in fixed|escalated|error) break;; esac
  sleep 3
done
curl -fsS "$B/api/state" | json "
r=s['runs'][-1] if s['runs'] else None
if r:
    print('   run', r['id'], r['status'], '(' + r['mode'] + ')')
    for e in r['events']: print('    -', e['kind'], ':', e['title'])
print('   live code:', s['live']['branch'], '@', s['live']['ref'])"
[ "$status" = fixed ] || fail "agent run ended as '$status'"

echo "== health check with the outage still on"
post /api/admin/check | json "assert s['ok'], [x for x in s['steps'] if not x['ok']]; print('   PASS 5/5 with fault', '429')"

post /api/admin/reset >/dev/null
echo "== E2E PASSED"
