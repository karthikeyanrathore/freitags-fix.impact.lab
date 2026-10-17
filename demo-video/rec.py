import sys, subprocess
from playwright.sync_api import sync_playwright
FPS=30; DUR=30; out=sys.argv[2]
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate',str(FPS),'-i','-',
  '-c:v','libx264','-preset','slow','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',out],stdin=subprocess.PIPE)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1280,'height':720})
    pg.goto('file://'+sys.argv[1]); pg.wait_for_timeout(300)
    for i in range(FPS*DUR):
        pg.evaluate(f'render({i/FPS})')
        ff.stdin.write(pg.screenshot(type='png'))
    b.close()
ff.stdin.close(); ff.wait()
