# Specs

We work spec-first: write or update a spec here, agree on it, then build against its acceptance criteria.

| Spec | What | Status |
|---|---|---|
| [001](001-broken-site-demo-video.md) | 30 s video of a customer hitting bugs on the mock pizza site | Done |
| [002](002-self-healing-agent-demo.md) | Agent detects an outage, fixes it via git, sends the owner a digest | Built, needs a live Claude run |
| [003](003-vercel-service.md) | Run the self-healing service on Vercel (GitHub fix branch → preview → production) | Draft, awaiting approval |

## How to use (people and Claude)
1. `git pull`, then read the spec you're working on.
2. Answer its open questions before writing code; record the answers in the spec.
3. Build only what the requirements say. Tick acceptance boxes as they pass.
4. Commit spec changes and code together, with a message that names the spec (e.g. `spec-002: add fault switch`).
5. New idea? Add a new numbered spec instead of growing an old one.
