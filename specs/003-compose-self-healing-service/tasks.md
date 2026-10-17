# Tasks: Self-healing shop as Docker Compose services

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup
- [x] T001 Initialize Spec Kit (`specify init --here --integration claude`) and write the constitution
- [x] T002 Create `services/{shop,order-api,agent}/` and `compose.yaml`

## Phase 2: Foundational
- [x] T003 [P] Valkey service in `compose.yaml` with a data volume
- [x] T004 [P] nginx routing in `services/shop/nginx.conf`

## Phase 3: User Story 1 - Customer orders while the vendor misbehaves (P1) 🎯 MVP
- [x] T005 [US1] `services/order-api/app.py`: cart add, cart, checkout, fault switch, `Idempotency-Key`, telemetry, state in Valkey
- [x] T006 [US1] `services/agent/app.py`: monitor loop, incidents, launch `agent/loop.py`, deploy by publishing to the live volume
- [x] T007 [US1] Dockerfiles for order-api (Python) and agent (Node 22 + Python + git)
- [x] T008 [US1] End-to-end check: fault 429 → alert → agent commit on `fix/…` → re-test PASS → deploy → health check 5/5 with fault on (verified natively with nginx + redis-server; Docker Hub isn't reachable from the build sandbox)

## Phase 4: User Story 2 - Owner sees what happened (P2)
- [x] T009 [US2] Agent serves `/api/state` and `/api/admin/*` in the shape `admin/index.html` already expects

## Phase 5: User Story 3 - Operator deploys on any VM (P3)
- [x] T010 [US3] README: VM run steps
- [ ] T011 [US3] `docker compose up -d --build` on the team VM; run the demo script from the README at `http://<vm>:8080/admin`
- [ ] T012 [US3] Live run with a real `ANTHROPIC_API_KEY` in `.env`

## Phase N: Polish
- [ ] T013 Optional `PUSH_FIXES=1` with a GitHub token so fix branches appear on GitHub
- [ ] T014 Next feature (004): the same images on kind

## Dependencies & Execution Order
T003–T004 before T005–T006; T008 after T005–T007; T011 needs a VM with Docker; T012 needs an API key.
