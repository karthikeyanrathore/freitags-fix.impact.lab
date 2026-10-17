"""Order API: the hosting vendor's ordering service, with a fault switch.

Endpoints (see site/VENDOR_API.md): POST /api/cart/add, GET /api/cart, POST /api/checkout,
plus POST /api/telemetry where customers' browsers report errors.
State lives in Valkey so the agent service can read and flip it.
"""
import json
import os
import random
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import redis

R = redis.Redis.from_url(os.environ.get("VALKEY_URL", "redis://valkey:6379/0"), decode_responses=True)
PORT = int(os.environ.get("PORT", "8001"))
IDEM_TTL = 3600


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def fault_now():
    """The failure to inject for this request, or None. Fails every other request so retries can succeed."""
    fault = R.get("fault") or "none"
    if fault == "none":
        return None
    return fault if R.incr("fault_counter") % 2 == 1 else None


def apply_add(body):
    key = f"cart:{body.get('cartId')}"
    R.hincrby(key, str(body.get("itemId")), 1)
    cart = {k: int(v) for k, v in R.hgetall(key).items()}
    return {"cart": cart, "count": sum(cart.values())}


def apply_checkout(body):
    key = f"cart:{body.get('cartId')}"
    if not R.hgetall(key):
        return None
    n = R.incr("orders")
    R.delete(key)
    return {"orderId": f"FP-{1000 + n}", "slot": body.get("slot")}


def apply_option(body):
    """Store the customer's in-progress choices for one pizza (size, toppings)."""
    line = str(body.get("lineId"))[:64]
    options = body.get("options") or {}
    R.set(f"draft:{body.get('cartId')}:{line}", json.dumps(options), ex=IDEM_TTL)
    return {"lineId": line, "options": options}


def apply_once(key, apply, body):
    """Apply at most once per Idempotency-Key; returns the stored result on repeats."""
    if key:
        cached = R.get(f"idem:{key}")
        if cached:
            return json.loads(cached)
        if not R.set(f"idem-lock:{key}", 1, nx=True, ex=30):  # same key in flight: wait for its result
            for _ in range(50):
                time.sleep(0.05)
                cached = R.get(f"idem:{key}")
                if cached:
                    return json.loads(cached)
    result = apply(body)
    if key and result is not None:
        R.set(f"idem:{key}", json.dumps(result), ex=IDEM_TTL)
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, status=200, headers=None):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def vendor_post(self, apply, body):
        key = self.headers.get("Idempotency-Key")
        time.sleep(random.uniform(0.03, 0.09))
        fault = fault_now()
        if fault in ("429", "503"):
            headers = {"Retry-After": "1"} if fault == "429" else {}
            return self.send_json({"error": "Too Many Requests" if fault == "429" else "Service Unavailable"},
                                  int(fault), headers)
        if fault == "504":  # applied upstream, but the gateway times out before answering
            apply_once(key, apply, body)
            time.sleep(1.2)
            return self.send_json({"error": "Gateway Timeout"}, 504)
        result = apply_once(key, apply, body)
        if result is None:
            return self.send_json({"error": "Cart is empty"}, 400)
        self.send_json(result)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/cart":
            cart_id = parse_qs(url.query).get("cartId", [""])[0]
            cart = {k: int(v) for k, v in R.hgetall(f"cart:{cart_id}").items()}
            return self.send_json({"cart": cart, "count": sum(cart.values())})
        if url.path == "/healthz":
            R.ping()
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        path, body = urlparse(self.path).path, self.body()
        if path == "/api/cart/add":
            return self.vendor_post(apply_add, body)
        if path == "/api/checkout":
            return self.vendor_post(apply_checkout, body)
        if path == "/api/cart/option":
            return self.vendor_post(apply_option, body)
        if path == "/api/telemetry":  # errors seen by real customers' browsers
            finding = {"ts": now(), "source": "customer browser", "endpoint": str(body.get("endpoint"))[:80],
                       "status": body.get("status"), "action": str(body.get("action"))[:80],
                       "message": str(body.get("message"))[:200]}
            R.rpush("findings", json.dumps(finding))
            R.ltrim("findings", -100, -1)
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"order-api listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
