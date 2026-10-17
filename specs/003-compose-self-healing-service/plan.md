# Implementation Plan: Self-healing shop as Docker Compose services

**Branch**: `003-compose-self-healing-service` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

## Summary
Split the single-process demo (`server.py`) into three containers behind nginx, with Valkey as shared state, so it runs on any VM with `docker compose up`. The agent keeps its real git workflow by mounting the repo; "deploy" copies the tested fix into a volume nginx serves.

## Technical Context
**Language/Version**: Python 3.12 (order-api), Python 3.11 + Node.js 22 (agent), plain HTML/JS (shop)
**Primary Dependencies**: nginx 1.27, Valkey 8, redis-py 5.2, Anthropic Python SDK, git
**Storage**: Valkey (fault, carts, idempotency, orders, findings); agent run records in memory + `.demo/runs/*.json`
**Testing**: synthetic customer `monitor/healthcheck.mjs`; end-to-end outage → fix → order run
**Target Platform**: Linux VM with Docker Engine + compose plugin; later kind
**Project Type**: web app (static front end + 2 Python services + gateway)
**Performance Goals**: each customer action < 4 s (health check step budget)
**Constraints**: open source only; no secrets in git; deadline 15:00 freeze
**Scale/Scope**: single shop, demo traffic

## Constitution Check
- I. Working demo first: ✅ reuses `agent/`, `monitor/`, `site/`, `admin/` unchanged; `server.py` kept as fallback.
- II. Claude in the product: ✅ `agent/claude.py`, prompts in `prompts/`; rehearsal labelled.
- III. Open source, runs anywhere: ✅ nginx, Valkey, Python, Node, git; plain compose.
- IV. Every fix in git, tested first: ✅ `fix/<run-id>` commits, deploy only after PASS.
- V. Plain language: ✅ digest unchanged.

## Project Structure

### Documentation (this feature)
```text
specs/003-compose-self-healing-service/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)
```text
compose.yaml                  # shop, order-api, agent, valkey
services/
├── shop/nginx.conf           # serves live site + /admin, routes /api/* to services
├── order-api/{app.py,Dockerfile}   # vendor API, fault switch, idempotency, telemetry
└── agent/{app.py,Dockerfile}       # monitor, incidents, agent loop, deploy, admin API
agent/  monitor/  prompts/  site/  admin/   # unchanged, shared with server.py
```

**Structure Decision**: one repo, one compose file, three services. The monitor lives in the agent service because it only exists to trigger the agent.

## Routing

| Path | Service |
|---|---|
| `/` , `/cart-client.js` | shop: files from volume `live-site` (what the agent last deployed) |
| `/admin/` | shop: `admin/` from the repo |
| `/api/cart*`, `/api/checkout`, `/api/telemetry` | order-api:8001 |
| `/api/state`, `/api/admin/*` | agent:8002 |

## Complexity Tracking
| Choice | Why | Simpler alternative rejected because |
|---|---|---|
| Valkey | order-api and agent are separate processes and must share fault/cart state | In-memory state can't be shared across containers |
| Repo bind-mounted into agent | fixes must be real git commits with history | Baking code into the image loses the git history and the fix branches |
