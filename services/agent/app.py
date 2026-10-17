"""Agent service: monitor + incidents + the self-healing agent + admin API.

- Runs the synthetic health check (monitor/healthcheck.mjs) against the shop every MONITOR_INTERVAL seconds.
- Opens an incident on failure and (with Autopilot) launches the agent loop in agent/loop.py.
- "Deploy" copies the fixed site/ into LIVE_DIR, the folder the shop container serves.
- Admin API: GET /api/state, POST /api/admin/{fault,monitor,autopilot,check,agent,reset}.
The repo is mounted at REPO_DIR so fixes are real git commits on fix/<run-id> branches.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import redis

ROOT = Path(os.environ.get("REPO_DIR", "/repo")).resolve()
LIVE = Path(os.environ.get("LIVE_DIR", "/live"))
SHOP_URL = os.environ.get("SHOP_URL", "http://shop")
PORT = int(os.environ.get("PORT", "8002"))
MONITOR_INTERVAL = int(os.environ.get("MONITOR_INTERVAL", "8"))
R = redis.Redis.from_url(os.environ.get("VALKEY_URL", "redis://valkey:6379/0"), decode_responses=True)

sys.path.insert(0, str(ROOT))
from agent import claude, loop  # noqa: E402


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


lock = threading.RLock()
S = {
    "monitoring": True,
    "autopilot": True,
    "live_site": str(ROOT / "site"),   # source of the code that is live (repo site/ or a fix worktree)
    "live_ref": "",
    "live_branch": "",
    "checks": [],
    "incident": None,
    "runs": [],
    "agent_busy": False,
}


def publish(site_dir, ref, branch):
    """Deploy: copy site_dir into the folder the shop serves."""
    tmp = LIVE.parent / (LIVE.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(site_dir, tmp)
    for p in LIVE.iterdir() if LIVE.exists() else []:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    LIVE.mkdir(parents=True, exist_ok=True)
    for p in tmp.iterdir():
        shutil.move(str(p), LIVE / p.name)
    shutil.rmtree(tmp, ignore_errors=True)
    with lock:
        S["live_site"], S["live_ref"], S["live_branch"] = str(site_dir), ref, branch


# ---------- monitor, incidents, agent ----------

def run_healthcheck(client_path=None):
    client_path = client_path or str(Path(S["live_site"]) / "cart-client.js")
    out = subprocess.run(["node", str(ROOT / "monitor/healthcheck.mjs"), "--base", SHOP_URL, "--client", client_path],
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
        "severity": "critical" if any(s.get("endpoint") == "/api/cart/add" for s in failed) else "warning",
        "summary": f"{len(failed)} of {len(check['steps'])} checks failing"
                   + (f" (HTTP {', '.join(statuses)})" if statuses else ""),
        "fault_injected": R.get("fault") or "none",
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
        try:
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
        except Exception:
            traceback.print_exc()


def customer_errors(limit=15):
    return [json.loads(x) for x in R.lrange("findings", -limit, -1)]


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
        publish(site_dir, ref, branch)

    def customer_errors(self):
        return customer_errors()

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
        incident = open_incident(check)
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
    R.set("fault", "none")
    R.set("fault_counter", 0)
    for pattern in ("cart:*", "idem:*", "idem-lock:*"):
        for k in R.scan_iter(pattern):
            R.delete(k)
    R.delete("findings")
    publish(ROOT / "site", git("rev-parse", "HEAD"), git("rev-parse", "--abbrev-ref", "HEAD"))
    with lock:
        S.update(checks=[], incident=None, runs=[] if not S["agent_busy"] else S["runs"])
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT)


def public_state():
    with lock:
        return {
            "fault": R.get("fault") or "none", "monitoring": S["monitoring"], "autopilot": S["autopilot"],
            "mode": "rehearsal" if claude.use_rehearsal() else "claude", "model": claude.MODEL,
            "live": {"ref": S["live_ref"][:8], "branch": S["live_branch"],
                     "site": os.path.relpath(S["live_site"], ROOT)},
            "orders": int(R.get("orders") or 0), "checks": S["checks"][-12:], "findings": customer_errors(25),
            "incident": S["incident"], "runs": S["runs"][-10:], "agent_busy": S["agent_busy"],
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, status=200):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
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
        path = urlparse(self.path).path
        if path == "/api/state":
            return self.send_json(public_state())
        if path == "/healthz":
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        path, body = urlparse(self.path).path, self.body()
        if path == "/api/admin/fault":
            mode = body.get("mode") if body.get("mode") in ("none", "429", "503", "504") else "none"
            R.set("fault", mode)
            R.set("fault_counter", 0)
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
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"])
    R.setnx("fault", "none")
    publish(ROOT / "site", git("rev-parse", "HEAD"), git("rev-parse", "--abbrev-ref", "HEAD"))
    threading.Thread(target=monitor_loop, daemon=True).start()
    mode = "REHEARSAL (no ANTHROPIC_API_KEY, canned agent answers)" if claude.use_rehearsal() else f"Claude ({claude.MODEL})"
    print(f"agent listening on :{PORT} · shop at {SHOP_URL} · {mode}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
