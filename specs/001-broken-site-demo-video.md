# Spec 001 · Broken pizza site demo video

**Status:** Done (as-built) · **Owner:** Sibu · **Code:** [`demo-video/`](../demo-video/)

## Goal
A 30-second video showing a customer trying to order from a mock pizza site and failing because of visible bugs. It opens the demo by showing the pain before the agent fixes anything.

## Requirements
- R1. Fictional brand only (Crust & Co., `crustandco.example`). No real brands or personal data.
- R2. 30 s, 1280×720, 30 fps, MP4 (H.264, yuv420p) so it plays anywhere.
- R3. Each bug gets an on-screen caption and a red dashed outline while it's shown.
- R4. Fully reproducible from source: deterministic frames, no screen recording.

## Bugs shown (timeline)
| # | Time | Bug | Category |
|---|---|---|---|
| 1 | 3–8 s | Hero image 404, promo says `$undefined` | Broken asset / config |
| 2 | 8–12 s | Layout shift: click lands on a sponsored pizza | UX / CLS |
| 3 | 12–16 s | No loading guard: 3 clicks, cart 1 → 4 | "Add buttons must register" (requirement) |
| 4 | 16–19 s | Raw `{{ pizza.name }}` and `$NaN` price | Rendering |
| 5 | 19–24 s | 10% coupon makes total −$1,240.00 | Business logic |
| 6 | 24–27 s | Checkout hangs at 99%, then HTTP 500 | Availability (requirement) |
| — | 27–30 s | End card: "6 bugs. 30 seconds. 0 pizzas." | |

## Design
- `scene.html`: single file; `render(t)` sets the whole page state for time `t`. Cursor path is keyframes (`K`) measured from real element positions; clicks in `CLICKS`; captions in `CAPS`.
- `rec.py`: headless Chromium (Playwright) captures 900 PNGs and pipes them to ffmpeg.

## Acceptance (verified)
- [x] Duration 30.0 s, 1280×720, 30 fps
- [x] All six captions appear and match the bug on screen
- [x] Toasts don't cover the cart badge
- [x] Re-render command in `demo-video/README.md` works

## Known gaps / follow-ups
- Bugs here are mostly front-end. The team's demo story (see [`demo-requirements.md`](../demo-requirements.md)) centres on **availability errors (429/503/504)** and lost "add" clicks. Spec 002 covers that.
- No audio or voiceover.
