# Feature Specification: Self-healing shop as Docker Compose services

**Feature Branch**: `003-compose-self-healing-service` (worked on `main`)
**Created**: 2026-10-17
**Status**: Implemented, verified locally; VM deployment pending
**Input**: "Start with a docker compose file with the relevant services which I can deploy anywhere, preferably a VM. Once we have a working solution, we can consider deploying it to a VM running kind." Use open-source components only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer orders while the vendor misbehaves (Priority: P1)
A customer orders pizza on the shop. The hosting vendor's ordering API starts failing (429/503/504). Within seconds the self-healing agent detects it, ships a tested fix, and the customer can order again even though the vendor is still failing.

**Why this priority**: This is the product. Without it there is no demo.

**Independent Test**: `docker compose up`, add a pizza (works), switch the fault to 429 in the admin page (customer add fails), wait for the agent run to finish, add a pizza and check out (works) with the fault still on.

**Acceptance Scenarios**:
1. **Given** the stack is up and no fault, **When** a customer adds a pizza, **Then** the cart updates.
2. **Given** fault 429 is on and the original cart code is live, **When** a customer adds a pizza, **Then** the request fails and the browser reports it to `/api/telemetry`.
3. **Given** fault 429 is on, **When** the monitor's health check fails, **Then** an incident opens and (Autopilot) the agent runs.
4. **Given** the agent's fix passes the health check, **When** it deploys, **Then** the shop serves the fixed code and a full order succeeds with the fault still on.

### User Story 2 - Owner sees what happened (Priority: P2)
The owner opens `/admin` and sees the alert, the agent's timeline (evidence, diagnosis, commit and diff, re-test, deploy) and a plain-language digest.

**Independent Test**: after a run, `/admin` shows the run with status `fixed` and the digest.

### User Story 3 - Operator deploys on any VM (Priority: P3)
An operator clones the repo on a VM with Docker, optionally adds `ANTHROPIC_API_KEY` to `.env`, runs `docker compose up -d --build`, and opens port 8080.

**Independent Test**: on a fresh VM, the commands in the README bring up all four containers and the shop answers on `:8080`.

### Edge Cases
- No API key: the agent runs in rehearsal mode (canned diagnosis, clearly labelled); everything else is real.
- Fix fails the health check: one more attempt with the new test results; then escalate without deploying.
- 504 after the request was applied: retries with the same `Idempotency-Key` must not double-add.
- Agent already running: further launches are refused.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST run as 3 services plus a datastore: `shop` (gateway + static), `order-api`, `agent`, `valkey`.
- **FR-002**: `order-api` MUST implement the vendor contract in `site/VENDOR_API.md`, including the fault switch and `Idempotency-Key`.
- **FR-003**: Fault mode, carts, idempotency keys, orders and customer error reports MUST live in Valkey so both services see the same state.
- **FR-004**: `agent` MUST run the synthetic health check every 8 s against the shop through the gateway, using the live cart client code.
- **FR-005**: `agent` MUST commit each fix to `fix/<run-id>` in the mounted repo, re-test it, and deploy only on pass by publishing the fixed `site/` to the volume `shop` serves.
- **FR-006**: All runtime components MUST be open source.
- **FR-007**: Secrets MUST come from `.env` / environment only.
- **FR-008**: The local single-process `server.py` MUST keep working as a fallback.

### Key Entities
- **Fault**: `none | 429 | 503 | 504`, plus a counter so every other request fails.
- **Cart / Order / Idempotency record**: vendor data in Valkey.
- **Finding**: an error reported by a customer's browser.
- **Incident**: an open alert from a failing health check.
- **Agent run**: events (alert, evidence, diagnosis, commit, re-test, deploy, digest), status, digest.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: From fault on to fixed code live in under 60 s (rehearsal) with the default 8 s monitor interval.
- **SC-002**: After the fix, the health check passes 5/5 with the fault still on.
- **SC-003**: Every deployed fix is a git commit on a `fix/…` branch.
- **SC-004**: `docker compose up -d --build` on a VM with Docker needs no other installs.

## Assumptions
- The VM has Docker Engine with the compose plugin and can pull from Docker Hub.
- The repo is cloned on the VM; the agent writes fix branches into that clone (push to GitHub is optional, `PUSH_FIXES=1`).
- One shop instance; Valkey persistence is a convenience, not a requirement.
- kind/Kubernetes is a later feature (004).
