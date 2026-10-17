# Broken pizza site · 30-second demo video

`crust-and-co-broken-site-demo.mp4` (1280×720, 30 fps, no audio) shows a user trying to order from the fictional **Crust & Co.** site and hitting six bugs:

1. Hero image 404, promo banner shows `$undefined`
2. Layout shift: the click lands on a sponsored pizza
3. No loading guard: three clicks on "Add to cart" and the cart jumps from 1 to 4
4. Raw template tags and a `$NaN` price on the menu
5. A 10% coupon makes the total −$1,240.00
6. Checkout hangs at 99%, then returns HTTP 500

## How it's made
- `scene.html` draws every frame as a function of time (`render(t)`), including the fake cursor and captions.
- `rec.py` opens it in headless Chromium, captures 900 frames and encodes them with ffmpeg.

## Re-render
```bash
pip install playwright && playwright install chromium   # ffmpeg must be installed too
python3 rec.py "$PWD/scene.html" crust-and-co-broken-site-demo.mp4
```
Edit the `CAPS`, `CLICKS` and `K` (cursor keyframes) arrays in `scene.html` to change timing or bugs.

Credits: Playwright (Apache-2.0), FFmpeg (LGPL/GPL), DejaVu fonts.

## Self-healing journey video (1:44)

`freitags-self-healing-journey.mp4` (1920×1080, 30 fps, no audio) is the 6-step story: order page → topping save fails and the customer is asked to retry → the self-healing agent diagnoses, commits, re-tests and deploys the fix → retry works, checkout → happy customer → postmortem in the admin page.

It's scripted animation (`journey.html`, rendered by `rec_journey.py`). The diff, commit message and owner summary come from the agent's real output. Topping customization, the retry prompt and the postmortem page are not in the app yet.

```bash
python3 rec_journey.py journey.html freitags-self-healing-journey.mp4   # ~7 min
```
