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

## Self-healing journey video (2:00)

`freitags-self-healing-journey.mp4` (1920×1080, 30 fps, no audio):

- **0:00–0:29, intro:** a "Freitags Fix Agent" title, then the problem card (Friday 7 pm outage and the cited Calyptix/ITIC 2025 downtime figure). Then a split screen of two fictional shops on the same vendor, Freitags Pizza and Kiezkorb Groceries, both hitting 429, 503 and 504 errors until the customers give up.
- **0:29–2:00, the 5-step story:** a topping save fails and the customer is asked to retry → the agent diagnoses, commits, re-tests and deploys the fix → retry works and checkout → happy customer → postmortem in the admin page.
- The transition cards show the Freitags Fix Agent wordmark behind the text.

It's scripted animation (`journey.html`, rendered by `rec_journey.py`). The diff, commit message and owner summary come from the agent's real output. Topping customization, the retry prompt and the postmortem page are not in the app yet.

```bash
python3 rec_journey.py journey.html freitags-self-healing-journey.mp4   # ~8 min, length comes from window.TOTAL
```
