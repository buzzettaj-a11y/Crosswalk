"""
Take the screenshots the user guide and the slideshow are built from.

Runs the tool against the example files, walks every stage, and writes one
picture per stage and per important element into docs/screenshots/. Run it
again whenever the interface changes, then rebuild the guide and the deck:

    python tools/take_screenshots.py
    python tools/make_docs.py

The example files hold made-up records, so nothing here is client data.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
PORT = 8798
BASE = f"http://127.0.0.1:{PORT}"


def post(path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())


async def main():
    from playwright.async_api import async_playwright
    os.makedirs(OUT, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "crosswalk_server:api",
                               "--host", "127.0.0.1", "--port", str(PORT)],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE + "/api/alive", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        post("/api/reset", {})
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1400, "height": 1000})
            await page.goto(BASE + "/")
            await page.wait_for_timeout(900)

            async def shot(name, full=False):
                await page.mouse.move(700, 500)
                await page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
                print("  ", name)

            async def screen(s):
                await page.evaluate(f"() => {{ UI.screen='{s}'; load('{s}'); }}")
                await page.wait_for_timeout(1200)

            await shot("00_check")
            await page.click('[data-act="continue"]')
            await page.wait_for_timeout(700)
            await page.click('[data-act="example"]')
            await page.wait_for_timeout(2500)
            await shot("01_sources")
            await page.locator("[data-table-preview]").first.click()
            await page.wait_for_timeout(1200)
            await shot("01b_sources_showdata")
            sch = json.loads(urllib.request.urlopen(BASE + "/api/ui?screen=schema").read())["schema"]["fields"]
            for f in sch:
                if f.get("role") == "Client_ID":
                    f["required"] = False
            post("/api/schema", {"schema": sch})
            await screen("schema")
            await shot("02_schema")
            await screen("prepare")
            await shot("03_prepare")
            await screen("map")
            await shot("04_map")
            await screen("programs")
            await shot("05_programs")
            await page.click('[data-act="prog-preview"]')
            await page.wait_for_timeout(6000)
            await shot("05b_programs_preview", full=True)
            await screen("run")
            await shot("06_run")
            post("/api/express/run", {"despite_warnings": True})
            for _ in range(100):
                if json.loads(urllib.request.urlopen(BASE + "/api/run/status").read())["state"] != "running":
                    break
                time.sleep(0.3)
            await screen("review")
            await shot("07_review", full=True)
            if await page.locator("[data-dupopen]").count():
                await page.locator("[data-dupopen]").first.click()
                await page.wait_for_timeout(700)
                await shot("07b_review_duplicates", full=True)
            gs = json.loads(urllib.request.urlopen(BASE + "/api/ui?screen=review").read())["review"]["groups"]
            if gs:
                post("/api/review/group", {"gid": gs[0]["id"], "decision": "sent"})
                await screen("queue")
                await shot("07c_queue", full=True)
            await screen("summary")
            await shot("08_summary", full=True)
            await screen("export")
            await shot("09_export", full=True)
            await page.evaluate("() => { UI.auditReturn='export'; UI.auditData=null; UI.screen='audit'; render(); loadAudit(); }")
            await page.wait_for_timeout(1500)
            await shot("10_audit")
            await page.evaluate("() => { UI.helpOpen='stage:review'; render(); }")
            await page.wait_for_timeout(300)
            await shot("11_help")
            await browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    asyncio.run(main())
