> 👋 **Starter for Claude Impact Lab teams.** Fill in each section below as you build and delete this note.
>
> 📅 **Agenda, rules, deadline and judging** are in the event repo: **[claude-impact-lab-berlin-2026-10-17](https://github.com/Claude-Community-Berlin/claude-impact-lab-berlin-2026-10-17)**. Read it first.
>
> ✅ **When you're finished:** record a 2-minute demo video, then submit with the **[submission form](https://tally.so/r/1WPr9Q)** before **16:00**. One submission per team.
>
> 🔑 Set your API key first: `cp .env.example .env`, then paste your key into `.env` (it's git-ignored, never commit it).

# Freitags Fix Agent

**One line:** An AI agent that keeps a small business's website taking orders. It spots outages, fixes them on its own and explains what happened to the owner in plain language, starting with a Berlin pizzeria.

## The problem
It's 7 pm on a Friday, one of the busiest nights of the week, and a Berlin pizzeria's online ordering stops working. The owner can't read code, the web agency won't pick up until Monday, and every hungry customer who can't order simply goes next door. In a 2025 survey of small businesses, 37% said a single hour of downtime costs them $1,000 to $5,000 ([Calyptix/ITIC](https://www.calyptix.com/?p=6720)). Big companies already use AI to keep their sites running around the clock. We think every small business should have the same help, simple enough to switch on without technical skills, so owners start to see AI as a partner in growing their business, not something only tech companies use.

## What it does
- **Watches the shop day and night.** A test customer places an order every few seconds, and errors that real customers hit are reported automatically.
- **Raises an alert the moment ordering breaks**, for example when the hosting provider is overloaded or times out on a Friday night.
- **Launches a Claude agent that fixes it.** The agent finds the cause, writes a fix and tests it before it goes live, with no action needed from the owner.
- **Keeps a full record.** Every fix is saved in git history with what changed and why.
- **Tells the owner what happened in plain language:** what broke, how it affected customers, what was changed and whether it's fixed now.
- **Shows everything in one admin panel:** the alerts, each step the agent took, the code change and the live shop.

## How Claude is used
When the health check fails, a Claude agent (`claude-opus-5-5`, via the Anthropic API) gets the alert telemetry, errors reported from customers' browsers, recent git history, the site's cart code and the hosting vendor's API notes. It returns, as structured JSON, a diagnosis, the root cause, a code fix, a commit message, a risk note and a plain-language digest for the shop owner. The agent commits the fix to its own `fix/…` branch, re-runs the health check, and only switches the live site to the fix if it passes. If it fails, Claude gets a second try with the new test results. Prompts are in [`prompts/`](prompts/). The loop is in [`agent/`](agent/).

## How to run it
Needs Python 3.9+, Node 18+ and git.
```bash
cp .env.example .env              # paste your ANTHROPIC_API_KEY into .env
python3 -m venv .venv && .venv/bin/pip install anthropic
.venv/bin/python server.py        # then open http://127.0.0.1:8000/admin
```
### Run on a VM with Docker Compose (3 services + Valkey)
Needs Docker Engine with the compose plugin. Everything is open source: nginx, Python, Node.js, git, Valkey.
```bash
git clone https://github.com/karthikeyanrathore/freitags-fix.impact.lab && cd freitags-fix.impact.lab
cp .env.example .env              # optional: paste your ANTHROPIC_API_KEY
docker compose up -d --build      # then open http://<vm-ip>:8080/admin
```

| Container | Role |
|---|---|
| `shop` (nginx) | Serves the live shop and `/admin`, routes `/api/*` to the services below |
| `order-api` | The vendor's ordering API with the fault switch and idempotency keys |
| `agent` | Health check every 8 s, incidents, Claude diagnosis, fix commits on `fix/…` branches, re-test, deploy |
| `valkey` | Shared state between `order-api` and `agent` |

The agent writes fix branches into the repo clone on the VM (`git branch --list 'fix/*'`). Spec: [`specs/003-compose-self-healing-service/`](specs/003-compose-self-healing-service/).

With no API key the agent runs in **rehearsal mode**: the diagnosis is a canned answer (clearly labelled in the admin panel), and everything else is real (alert, git commit, re-test, deploy, digest).

### Demo script (admin panel at `/admin`, the shop is at `/` and also embedded on the right)
1. Add a pizza in the customer view: it works.
2. Click **429 Too many requests** (or 503 / 504). Click Add in the shop: the customer sees an error, and it shows up under **Bug findings from customers**.
3. Within ~8 s the monitor's health check fails and an **alert** appears (or click **Run health check now**). With **Autopilot** on, the agent launches by itself (or click **🤖 Launch agent**).
4. Watch the **Agent run** timeline: alert → evidence → Claude's diagnosis → commit (open **Code change** to see the diff) → re-test PASS → deploy.
5. The **Owner's inbox** gets the digest, and the customer view reloads on the fixed code. Add a pizza and check out: it works even though the vendor outage is still on.
6. **Reset demo** puts the original code back live and turns the fault off. Fix branches stay in `git branch --list 'fix/*'` as history. Run with `PUSH_FIXES=1` to also push each fix branch to GitHub and link the commit in the digest.

**Live link (if any):** <link>

## Screenshots / demo
🎬 **[Watch the 2-minute demo video](https://drive.google.com/file/d/1sZD-eK_KXpYB-PhEOCqz_jFhCkm9sSTA/view?usp=sharing)** (Google Drive)

## Team
Teams of 5 (at least 1 builder, 1 product or design, 1 domain expert; plus founder or anyone). Link each name to a GitHub or LinkedIn profile, and replace the example row with your team.

| Name | Role / background |
|---|---|
| Karthikeyan | |
| Sibu | |
| Kimberly | |
| Suraj | |

## Credits
Anthropic API and Python SDK (MIT). Everything else is the Python and Node standard libraries. Playwright and FFmpeg were used for the demo video (see [`demo-video/`](demo-video/)).
