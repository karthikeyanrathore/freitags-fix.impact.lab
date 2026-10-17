# Spec 002 · Self-healing pizza site (agent loop demo)

**Status:** Draft, needs team review · **Source:** [`demo-requirements.md`](../demo-requirements.md) · **Deadline:** feature freeze 15:00

## Audience and problem (one line each, for the README)
- **Who:** small food business owners whose website is run by a third-party vendor.
- **Problem:** when the site breaks they lose orders, can't diagnose it, and wait on the vendor.
- **Demo:** a Claude agent detects the outage, diagnoses it, ships a tested fix through git, and sends the owner a plain-language digest.

## User story
As a pizza shop owner, I want my site's outages detected and fixed without me, and a short summary of what happened, so that I keep taking orders and understand what the AI did.

## Requirements
- R1. Mock pizza site (in `site/`) with a **fault switch** that can trigger HTTP 429, 503 or 504 on add-to-cart or checkout.
- R2. Every "Add to cart" click must register exactly once (no lost or duplicated adds).
- R3. A **health check** (synthetic test) hits the site and reports failures as structured telemetry (status code, endpoint, latency, timestamp).
- R4. On failure, a **Claude agent** (Anthropic API) receives the telemetry plus relevant source files, and returns: diagnosis, proposed fix (as a code change), and risk note.
- R5. The fix is applied on a **git branch with a commit** (history is required), the health check re-runs, and only passes go forward (merge / deploy).
- R6. The owner receives a **digest**: what broke, impact, what was changed (commit link), test result, in plain language.
- R7. Prompts live in `prompts/`. API key from `.env` only.

## Demo script (≈2 min)
1. Site works: add a pizza, checkout succeeds. (15 s)
2. Flip fault switch → customers see 429/503. Optionally cut in the 30 s video from Spec 001. (20 s)
3. Health check fails → agent run starts; show its timeline (alert → diagnose → fix → commit). (45 s)
4. Health check re-runs green; site works again. (20 s)
5. Owner's digest appears (email/Slack-style card). (20 s)

## Proposed design (smallest version)
- `site/`: static site + tiny API (e.g. Vercel serverless or a local Python server) with the fault switch.
- `agent/`: one script: run health check → call Claude with telemetry + files → write patch → `git commit` on `fix/<id>` → re-run check → write `runs/<id>.json` and digest.
- `dashboard`: one HTML page that reads `runs/*.json` and shows the agent timeline + digest (this is the "artifact that demonstrates the failure pattern").

## Acceptance criteria
- [ ] Fault switch reliably produces 429, 503 and 504.
- [ ] Health check detects each within one run and records telemetry.
- [ ] Agent produces a diagnosis and a code change that makes the check pass for at least one fault (429 is enough for the demo).
- [ ] The fix shows up as a commit with a clear message in git history.
- [ ] Digest is readable by a non-technical owner (no stack traces in the main text).
- [ ] Whole loop runs end to end live in under 60 s.

## Out of scope (cut first if behind)
- Real vendor integration, real payments, multiple simultaneous faults, auto-merge to production without a passing check.

## Open questions
1. Deploy target for the demo: Vercel preview deploys, or run everything locally? (Local is safer for a live demo.)
2. How is the agent triggered: manual "run" button, cron, or webhook from the health check?
3. Digest channel: on-screen card only, or real email/Slack?
4. What does the "fix" actually change for a 429: retry with backoff + idempotency key on add-to-cart, or a config/rate-limit change?
5. Does `site/index.html` (existing) become the mock site, and who owns it?

## Tasks
1. Agree answers to open questions (15 min).
2. Fault switch + add-to-cart idempotency in `site/`.
3. Health check script + telemetry JSON.
4. Agent script + prompts in `prompts/`.
5. Git branch/commit + re-test step.
6. Dashboard page + digest.
7. Record 2-min video, fill in README.
