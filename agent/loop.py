"""The agent loop: alert -> diagnose with Claude -> commit fix on a branch -> re-test -> deploy -> owner digest."""
import os
import re
import subprocess
import time
from pathlib import Path

from agent import claude

ROOT = Path(__file__).resolve().parent.parent
WORKTREES = ROOT / ".demo/worktrees"
MAX_ATTEMPTS = 2
CONTEXT_FILES = ["site/cart-client.js", "site/VENDOR_API.md", "monitor/healthcheck.mjs"]


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def github_commit_url(sha):
    remote = git("remote", "get-url", "origin")
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    return f"https://github.com/{m.group(1)}/commit/{sha}" if m else None


def run(record, hooks):
    """record: dict for this run (mutated as we go). hooks: object from server.py with
    emit(kind, title, detail), healthcheck(client_path), deploy(site_dir, ref, branch), customer_errors(), live()."""
    alert = record["alert"]
    hooks.emit("alert", "Alert received", alert)

    live_site_dir, live_ref = hooks.live()
    live_root = Path(live_site_dir).parent
    files = {p: (live_root / p).read_text() for p in CONTEXT_FILES}
    git_log = git("log", "--oneline", "-8", live_ref)
    customer_errors = hooks.customer_errors()
    hooks.emit("context", "Collected evidence", {
        "files": list(files), "customer_errors": len(customer_errors), "live_code": live_ref[:8], "git_log": git_log})

    run_id = record["id"]
    branch = f"fix/{run_id}"
    wt = WORKTREES / run_id
    WORKTREES.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-q", "-b", branch, str(wt), live_ref)
    record["branch"] = branch

    rehearsal = claude.use_rehearsal()
    ask = claude.rehearsal_diagnose if rehearsal else claude.diagnose
    previous = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        hooks.emit("thinking", f"Asking Claude to diagnose (attempt {attempt})",
                   {"model": "rehearsal (no Claude call)" if rehearsal else claude.MODEL})
        t0 = time.time()
        result, meta = ask(alert, customer_errors, previous, git_log, files)
        meta["seconds"] = round(time.time() - t0, 1)
        hooks.emit("diagnosis", "Diagnosis", {
            "diagnosis": result["diagnosis"], "root_cause": result["root_cause"],
            "fix_summary": result["fix_summary"], "risk": result["risk"], **meta})

        for f in result["files"]:
            target = (wt / f["path"]).resolve()
            if not str(target).startswith(str((wt / "site").resolve()) + os.sep):
                raise RuntimeError(f"Claude proposed editing {f['path']}, which is outside site/. Refusing.")
            target.write_text(f["content"])
            files[f["path"]] = f["content"]
        git("add", "-A", "site", cwd=wt)
        msg = result["commit_message"].strip() + f"\n\nAgent-Run: {run_id}\nAttempt: {attempt}"
        git("commit", "-q", "-m", msg, cwd=wt)
        sha = git("rev-parse", "HEAD", cwd=wt)
        diff = git("show", "--stat", "--patch", "--format=commit %H%nAuthor: %an%nDate:   %ad%n%n%B", "HEAD", cwd=wt)
        commit = {"sha": sha, "branch": branch, "subject": msg.splitlines()[0], "diff": diff}
        if os.environ.get("PUSH_FIXES") == "1":
            git("push", "-q", "-u", "origin", branch, cwd=wt)
            commit["url"] = github_commit_url(sha)
        hooks.emit("commit", f"Committed fix to {branch}", commit)

        check = hooks.healthcheck(str(wt / "site/cart-client.js"))
        hooks.emit("retest", "Re-ran health check: " + ("PASS" if check["ok"] else "FAIL"), check)
        if check["ok"]:
            hooks.deploy(str(wt / "site"), sha, branch)
            hooks.emit("deploy", "Deployed fix to the live site", {"sha": sha, "branch": branch})
            digest = dict(result["digest"], commit=sha[:8], commit_url=commit.get("url"), branch=branch,
                          test="Passed", rehearsal=rehearsal)
            hooks.emit("digest", "Sent digest to the owner", digest)
            return digest
        previous = {"attempt": attempt, "fix_summary": result["fix_summary"],
                    "health_check_after_fix": [s for s in check["steps"] if not s["ok"]]}

    digest = {"headline": "Your website has a problem we couldn't fix automatically",
              "what_happened": result["digest"]["what_happened"],
              "customer_impact": result["digest"]["customer_impact"],
              "what_we_changed": "Nothing went live. The attempted fixes are saved for your web agency to review.",
              "status": "Needs a person. We've flagged it to your web agency.",
              "branch": branch, "test": "Failed", "rehearsal": rehearsal}
    hooks.emit("escalate", "Fix didn't pass the health check; escalated", digest)
    return digest
