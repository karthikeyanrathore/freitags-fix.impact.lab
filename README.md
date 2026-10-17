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

**CI/CD (GitHub Actions):** [`ci.yml`](ci/workflows/ci.yml) builds the stack on every push and runs [`scripts/e2e.sh`](scripts/e2e.sh) (429 outage → agent fix → health check 5/5). When CI passes on `main`, [`deploy.yml`](ci/workflows/deploy.yml) SSHes into the VM, runs [`scripts/deploy.sh`](scripts/deploy.sh) (`git pull` + `docker compose up -d --build`) and smoke-tests the public URL. Setup: repo secret `VM_SSH_KEY`; repo variables `VM_HOST`, `VM_USER`, `VM_APP_DIR` (optional `VM_PORT`). The workflow files are in [`ci/`](ci/) until someone with the `workflow` scope moves them to `.github/workflows/`.

The agent writes fix branches into the repo clone on the VM (`git branch --list 'fix/*'`). Spec: [`specs/003-compose-self-healing-service/`](specs/003-compose-self-healing-service/).

With no API key the agent runs in **rehearsal mode**: the diagnosis is a canned answer (clearly labelled in the admin panel), and everything else is real (alert, git commit, re-test, deploy, digest).

**Live link:** [shop](http://66.201.4.39:8080/) · [admin](http://66.201.4.39:8080/admin) (Nebius VM, Docker Compose)

## Screenshots / demo
🎬 **[Watch the 2-minute demo video](https://drive.google.com/file/d/1sZD-eK_KXpYB-PhEOCqz_jFhCkm9sSTA/view?usp=sharing)** (Google Drive)

## Team
Teams of 5 (at least 1 builder, 1 product or design, 1 domain expert; plus founder or anyone). Link each name to a GitHub or LinkedIn profile, and replace the example row with your team.

| Name | Role / background |
|---|---|
| Karthikeyan | Builder |
| Sibu | CTO |
| Kimberly | Founder |
| Suraj | Domain expert |

## Credits
Anthropic API and Python SDK (MIT). Everything else is the Python and Node standard libraries. Playwright and FFmpeg were used for the demo video (see [`demo-video/`](demo-video/)).
