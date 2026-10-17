# Freitags Pizza Self-Healing Shop Constitution

## Core Principles

### I. Working demo first
A demo that really runs beats perfect code. Build the smallest thing that demos well, cut scope early, and keep a working fallback (the local `server.py` and the recorded videos) at all times. Feature freeze 15:00, submission 16:00 on 17 Oct 2026.

### II. Claude is part of the product
The self-healing agent's diagnosis and fix come from Claude via the Anthropic API (`claude-opus-5-5`), with prompts kept in `prompts/`. Rehearsal mode (no API key) must be clearly labelled wherever it is shown.

### III. Open source, runs anywhere
Every runtime component is open source and runs from `docker compose up` on a plain VM (nginx, Python, Node.js, git, Valkey). No hosting-provider lock-in; the same images must later run on kind.

### IV. Every fix is in git, and tested before it goes live
The agent commits each fix to its own `fix/<run-id>` branch and only deploys it after the synthetic customer health check passes against the fixed code. History is never rewritten.

### V. Plain language for the owner
Anything the shop owner reads (digest, postmortem) is jargon-free: what happened, effect on customers, what changed, status. Technical detail is available but secondary.

## Security and data
- No secrets in git. `ANTHROPIC_API_KEY` and any tokens live in `.env` (git-ignored) or the host's secret store.
- Only fake sample data (menu, carts, orders). No real personal data.
- The agent may only edit files under `site/`; anything else is refused.

## Workflow
- Spec Kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, one numbered folder per feature in `specs/`.
- `git pull` before working; small commits that name the spec (e.g. `spec-003: …`); push after each step.
- Split work by folder so teammates don't edit the same file at once.

## Governance
This constitution and `CLAUDE.md` guide all work on this repo; where they differ, `CLAUDE.md` (event rules) wins. Amend by PR with a one-line reason.

**Version**: 1.0.0 | **Ratified**: 2026-10-17 | **Last Amended**: 2026-10-17
