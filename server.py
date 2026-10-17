"""Freitags Pizza self-healing demo server.

Serves the shop (/), the admin panel (/admin), the vendor's ordering API with a fault switch,
a background health-check monitor that raises alerts, and launches the Claude agent.
Run: .venv/bin/python server.py   (then open http://127.0.0.1:8000/admin)
"""
import json
import mimetypes
import os
import random
import subprocess
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8000"))
BASE = f"http://127.0.0.1:{PORT}"
MONITOR_INTERVAL = 8  # seconds between synthetic health checks


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip())


load_env()
from agent import claude, loop  # noqa: E402  (after .env is loaded)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


lock = threading.RLock()
S = {
    "fault": "none",           # none | 429 | 503 | 504
    "fault_counter": 0,
    "monitoring": True,
    "autopilot": True,
    "live_site": str(ROOT / "site"),
    "live_ref": git("rev-parse", "HEAD"),
    "live_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "carts": {},               # cartId -> {itemId: qty}
    "idempotency": {},         # key -> response body
    "orders": 0,
    "checks": [],              # recent health-check results
    "findings": [],            # customer-reported errors
    "incident": None,          # open alert
    "runs": [],                # agent runs, newest last
    "agent_busy": False,
}


# ---------- vendor ordering API with fault switch ----------

def fault_now():
    """Returns the failure to inject for this request, or None. Fails every other request so retries can succeed."""
    with lock:
        if S["fault"] == "none":
            return None
        S["fault_counter"] += 1
        return S["fault"] if S["fault_counter"] % 2 == 1 else None


def apply_add(body):
    with lock:
        cart = S["carts"].setdefault(str(body.get("cartId")), {})
        item = str(body.get("itemId"))
        cart[item] = cart.get(item, 0) + 1
        return {"cart": dict(cart), "count": sum(cart.values())}


def apply_checkout(body):
    with lock:
        cart = S["carts"].get(str(body.get("cartId"))) or {}
        if not cart:
            return None
        S["orders"] += 1
        S["carts"][str(body.get("cartId"))] = {}
        return {"orderId": f"FP-{1000 + S['orders']}", "slot": body.get("slot")}


def vendor_post(handler, apply, body):
    key = handler.headers.get("Idempotency-Key")
    time.sleep(random.uniform(0.03, 0.09))
    fault = fault_now()
    if fault in ("429", "503"):
        headers = {"Retry-After": "1"} if fault == "429" else {}
        return handler.send_json({"error": "Too Many Requests" if fault == "429" else "Service Unavailable"},
                                 int(fault), headers)
    if fault == "504":  # the request is applied upstream, but the gateway times out before answering
        with lock:
            if not (key and key in S["idempotency"]):
                result = apply(body)
                if key:
                    S["idempotency"][key] = result
        time.sleep(1.2)
        return handler.send_json({"error": "Gateway Timeout"}, 504)
    with lock:
        if key and key in S["idempotency"]:
            return handler.send_json(S["idempotency"][key])
        result = apply(body)
        if result is None:
            return handler.send_json({"error": "Cart is empty"}, 400)
        if key:
            S["idempotency"][key] = result
    handler.send_json(result)


# ---------- monitor, incidents, agent ----------

def run_healthcheck(client_path=None):
    client_path = client_path or str(Path(S["live_site"]) / "cart-client.js")
    out = subprocess.run(["node", str(ROOT / "monitor/healthcheck.mjs"), "--base", BASE, "--client", client_path],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "timestamp": now(), "steps": [], "error": out.stderr[-2000:]}


def record_check(result, source):
    with lock:
        S["checks"] = (S["checks"] + [dict(result, source=source)])[-30:]


def open_incident(check):
    failed = [s for s in check["steps"] if not s["ok"]]
    statuses = sorted({str(s["status"]) for s in failed if s.get("status")})
    alert = {
        "id": "INC-" + datetime.now().strftime("%H%M%S"),
        "opened": now(),
        "source": "synthetic health check",
        "severity": "critical" if any(s["endpoint"] == "/api/cart/add" for s in failed) else "warning",
        "summary": f"{len(failed)} of {len(check['steps'])} checks failing"
                   + (f" (HTTP {', '.join(statuses)})" if statuses else ""),
        "fault_injected": S["fault"],
        "health_check": check,
    }
    with lock:
        S["incident"] = alert
    if S["autopilot"]:
        launch_agent()
    return alert


def monitor_loop():
    while True:
        time.sleep(MONITOR_INTERVAL)
        if not S["monitoring"] or S["agent_busy"]:
            continue
        result = run_healthcheck()
        record_check(result, "monitor")
        with lock:
            incident = S["incident"]
        if not result["ok"] and incident is None:
            open_incident(result)
        elif not result["ok"] and incident and incident.get("status") != "agent running" and S["autopilot"] \
                and not incident.get("agent_tried"):
            launch_agent()
        elif result["ok"] and incident:
            with lock:
                incident.update(status="resolved", resolved=now())
                S["incident"] = None


class Hooks:
    def __init__(self, record):
        self.record = record

    def emit(self, kind, title, detail=None):
        with lock:
            self.record["events"].append({"ts": now(), "kind": kind, "title": title, "detail": detail})

    def healthcheck(self, client_path):
        result = run_healthcheck(client_path)
        record_check(result, "agent re-test")
        return result

    def deploy(self, site_dir, ref, branch):
        with lock:
            S["live_site"], S["live_ref"], S["live_branch"] = site_dir, ref, branch

    def customer_errors(self):
        with lock:
            return S["findings"][-15:]

    def live(self):
        with lock:
            return S["live_site"], S["live_ref"]


def launch_agent():
    with lock:
        if S["agent_busy"]:
            return None
        incident = S["incident"]
        S["agent_busy"] = True
    if incident is None:  # manual launch with no open alert: take a fresh reading first
        check = run_healthcheck()
        record_check(check, "agent pre-check")
        if check["ok"]:
            with lock:
                S["agent_busy"] = False
            return {"error": "Health check is passing; nothing to fix."}
        incident = open_incident(check)  # its autopilot launch is a no-op because agent_busy is set
    record = {"id": datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4],
              "started": now(), "status": "running", "alert": incident, "events": [],
              "mode": "rehearsal" if claude.use_rehearsal() else "claude"}
    with lock:
        S["runs"].append(record)
        incident.update(status="agent running", agent_tried=True, run_id=record["id"])

    def work():
        try:
            record["digest"] = loop.run(record, Hooks(record))
            record["status"] = "fixed" if record["digest"].get("test") == "Passed" else "escalated"
            if record["status"] == "fixed":
                with lock:
                    if S["incident"] is incident:
                        incident.update(status="resolved", resolved=now())
                        S["incident"] = None
        except Exception as e:
            record["status"] = "error"
            Hooks(record).emit("error", "Agent run failed", {"error": str(e), "trace": traceback.format_exc()[-3000:]})
            with lock:
                incident["status"] = "agent failed"
        finally:
            record["finished"] = now()
            (ROOT / ".demo/runs").mkdir(parents=True, exist_ok=True)
            (ROOT / f".demo/runs/{record['id']}.json").write_text(json.dumps(record, indent=2))
            with lock:
                S["agent_busy"] = False

    threading.Thread(target=work, daemon=True).start()
    return {"run_id": record["id"]}


def reset_demo():
    with lock:
        S.update(fault="none", fault_counter=0, live_site=str(ROOT / "site"), live_ref=git("rev-parse", "HEAD"),
                 live_branch=git("rev-parse", "--abbrev-ref", "HEAD"), carts={}, idempotency={}, checks=[],
                 findings=[], incident=None, runs=[] if not S["agent_busy"] else S["runs"])
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT)


def public_state():
    with lock:
        return {
            "fault": S["fault"], "monitoring": S["monitoring"], "autopilot": S["autopilot"],
            "mode": "rehearsal" if claude.use_rehearsal() else "claude", "model": claude.MODEL,
            "live": {"ref": S["live_ref"][:8], "branch": S["live_branch"],
                     "site": os.path.relpath(S["live_site"], ROOT)},
            "orders": S["orders"], "checks": S["checks"][-12:], "findings": S["findings"][-25:],
            "incident": S["incident"], "runs": S["runs"][-10:], "agent_busy": S["agent_busy"],
        }


# ---------- HTTP ----------

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

    def send_file(self, path):
        path = Path(path)
        if not path.is_file():
            return self.send_json({"error": "not found"}, 404)
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/cart":
            cart_id = parse_qs(url.query).get("cartId", [""])[0]
            with lock:
                cart = dict(S["carts"].get(cart_id, {}))
            return self.send_json({"cart": cart, "count": sum(cart.values())})
        if url.path == "/api/state":
            return self.send_json(public_state())
        if url.path in ("/admin", "/admin/"):
            return self.send_file(ROOT / "admin/index.html")
        site = Path(S["live_site"]).resolve()
        target = (site / (url.path.lstrip("/") or "index.html")).resolve()
        if not str(target).startswith(str(site)):
            return self.send_json({"error": "not found"}, 404)
        self.send_file(target)

    def do_POST(self):
        path, body = urlparse(self.path).path, self.body()
        if path == "/api/cart/add":
            return vendor_post(self, apply_add, body)
        if path == "/api/checkout":
            return vendor_post(self, apply_checkout, body)
        if path == "/api/telemetry":  # errors seen by real customers' browsers
            finding = {"ts": now(), "source": "customer browser", "endpoint": str(body.get("endpoint"))[:80],
                       "status": body.get("status"), "action": str(body.get("action"))[:80],
                       "message": str(body.get("message"))[:200]}
            with lock:
                S["findings"] = (S["findings"] + [finding])[-100:]
            return self.send_json({"ok": True})
        if path == "/api/admin/fault":
            with lock:
                S["fault"] = body.get("mode") if body.get("mode") in ("none", "429", "503", "504") else "none"
                S["fault_counter"] = 0
            return self.send_json(public_state())
        if path in ("/api/admin/monitor", "/api/admin/autopilot"):
            with lock:
                S["monitoring" if path.endswith("monitor") else "autopilot"] = bool(body.get("on"))
            return self.send_json(public_state())
        if path == "/api/admin/check":
            result = run_healthcheck()
            record_check(result, "manual")
            with lock:
                incident = S["incident"]
            if not result["ok"] and incident is None:
                open_incident(result)
            return self.send_json(result)
        if path == "/api/admin/agent":
            return self.send_json(launch_agent() or {"error": "Agent is already running."})
        if path == "/api/admin/reset":
            reset_demo()
            return self.send_json(public_state())
        self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    mode = "REHEARSAL (no ANTHROPIC_API_KEY, canned agent answers)" if claude.use_rehearsal() else f"Claude ({claude.MODEL})"
    print(f"Shop:  {BASE}/\nAdmin: {BASE}/admin\nAgent: {mode}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
