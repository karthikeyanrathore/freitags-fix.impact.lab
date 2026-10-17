# Spec 003 · Self-healing service on Vercel

**Status:** Draft, awaiting approval · **Builds on:** [002](002-self-healing-agent-demo.md) · **Target:** [`demo-video/freitags-self-healing-journey.mp4`](../demo-video/freitags-self-healing-journey.mp4) · **Freeze:** 15:00

## Goal
Run the self-healing pizza shop for real on Vercel: a public shop URL, a vendor API with a fault switch, and a Claude agent that detects the outage, commits a fix to GitHub, verifies it on a Vercel preview deployment, and promotes it to production. The owner sees a postmortem in the admin page.

## Why the local version can't just be uploaded
`server.py` keeps state in memory, runs a background monitor thread, and "deploys" by switching folders after a local `git commit`. Vercel functions are short-lived with no shared memory, no background threads and no writable git checkout. So:

| Local (spec 002) | Vercel (this spec) |
|---|---|
| In-memory state (cart, fault, incidents, runs) | Redis (Upstash, via Vercel Marketplace) |
| Monitor thread every 8 s | Health check triggered by customer error reports + admin button (+ cron if the plan allows) |
| `git commit` in a local worktree | GitHub API: commit to `fix/inc-<id>`, open a PR |
| Switch served folder = deploy | Vercel builds a **preview** for the branch → agent re-tests the preview → merges the PR → **production** deploy |
| Python server + Node health check | Node.js functions in `api/` (one language) |

## Architecture
- `public/` static shop (`index.html`, `cart-client.js`) and admin (`admin/index.html`).
- `api/cart/add`, `api/cart`, `api/checkout`: vendor API; reads the fault mode from Redis; honours `Idempotency-Key` (same rules as `site/VENDOR_API.md`).
- `api/telemetry`: customer browsers report failures; opens an incident when failures cross a threshold and kicks off the agent.
- `api/health`: synthetic customer. Fetches the target deployment's own `cart-client.js` and runs add/add/add/checkout against it, so it tests the code that is actually deployed.
- `api/admin/*`: fault switch, run health check, launch agent, reset, state.
- `api/agent`: the loop (`maxDuration` 300 s): alert → evidence (telemetry, customer errors, recent commits and files via GitHub API) → Claude diagnosis (structured JSON, prompts in `prompts/`) → commit + PR → wait for the Vercel preview URL (from GitHub deployment statuses) → health check on the preview → merge PR → wait for production → write run, digest and postmortem to Redis.
- Admin page: alert, live agent timeline, diff, owner digest, **postmortem** (from the video) with Approve.

## Requirements
- R1. Shop, vendor API and admin run on a public Vercel URL.
- R2. Fault switch (429/503/504) works on production and survives across function instances.
- R3. Every agent fix is a real commit on a `fix/…` branch with a PR, visible on GitHub.
- R4. A fix only reaches production after the health check passes on its preview deployment.
- R5. Owner digest and postmortem are plain language; no stack traces in the main text.
- R6. No secrets in git: `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, Redis credentials live in Vercel environment variables.
- R7. Rehearsal mode still works with no `ANTHROPIC_API_KEY` (canned diagnosis, clearly labelled).
- R8. The local version (`server.py`) keeps working as a fallback for the demo.

## Acceptance criteria
- [ ] Production URL serves the shop; adding a pizza and checking out works.
- [ ] Turning on 429 in admin makes the shop fail for customers.
- [ ] The agent run produces a commit + PR on GitHub, a passing preview check, a merged PR and a new production deployment.
- [ ] After the run, the shop works with the fault still on.
- [ ] Admin shows the timeline, digest and postmortem.
- [ ] End to end in under ~3 minutes (preview + production builds dominate).

## Plan (time-boxed)
| Slot | Work | Cut if late |
|---|---|---|
| 14:15–14:25 | Vercel project linked to the repo, Redis, env vars, `vercel.json` | |
| 14:25–14:45 | Port vendor API, fault switch, telemetry, health check, admin state to `api/`; first production deploy | |
| 14:45–15:00 | Agent function: Claude diagnosis → GitHub commit/PR → preview check → merge | Fall back to rehearsal diagnosis |
| stretch | Postmortem page + Approve, topping customizer + friendly retry prompt from the video | Cut first |
| 15:00 | Feature freeze; update README with live link | |

## Risks
- **Time:** one hour to freeze. The local version and the recorded video are the fallback.
- **Access:** the Vercel account must be able to import `karthikeyanrathore/freitags-fix.impact.lab` (Vercel GitHub app on that account), and the agent needs a GitHub token that can push branches and merge PRs.
- **Build time:** preview + production builds make the loop ~1–3 min instead of the 24 s shown in the video.
- **Cron:** frequent cron jobs may need a paid plan; customer error reports and the admin button trigger checks regardless.

## Open questions
1. Which Vercel account/team owns the project? (The connected Vercel account currently shows no projects or teams.)
2. Who creates the `GITHUB_TOKEN` (fine-grained, this repo only: Contents and Pull requests read/write)? The repo owner is karthikeyanrathore.
3. Fix deploy path: real **branch → preview → merge** (recommended, authentic) or an instant "live code" switch in Redis (faster, less real)?
4. Include the stretch items (customizer, retry prompt, postmortem) or freeze on the core loop?
