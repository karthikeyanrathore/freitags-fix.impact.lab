"""Render journey.html to MP4. Usage: python3 rec_journey.py journey.html out.mp4"""
import sys, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
FPS, DUR, SCALE = 30, 104, 1.5          # 1280x720 CSS px x1.5 = 1920x1080
src, out = Path(sys.argv[1]).resolve(), sys.argv[2]
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                       "-t", "119", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", out], stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=SCALE)
    pg.goto(src.as_uri()); pg.wait_for_timeout(500)
    for i in range(FPS * DUR):
        pg.evaluate(f"render({i / FPS})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
    b.close()
ff.stdin.close(); ff.wait()
