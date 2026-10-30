"""
Layout: the page never scrolls sideways.

Every screen is rendered in a real browser at five widths, with data loaded so
the grids and tables are full, and the page width is measured. Anything wider
than the window must sit inside a box that scrolls on its own; the page itself
never does. Element sizes are checked too, so a dropdown holding a short value
cannot quietly grow to fill the screen.

Run: python tests/test_layout.py   (needs playwright; skips cleanly without it)
"""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

try:
    from playwright.async_api import async_playwright
except Exception:
    print("LAYOUT TESTS: SKIPPED (playwright not installed)")
    sys.exit(0)

PORT = 8797
BASE = f"http://127.0.0.1:{PORT}"
results = []


def check(label, cond):
    results.append((label, bool(cond)))


def post(path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"},
                               method="POST")
    return json.loads(urllib.request.urlopen(r).read())


FIND = """() => {
  const vw = document.documentElement.clientWidth;
  let widest = 0;
  document.querySelectorAll('body *').forEach(el => {
    if (el.closest('.pvscroll, .rail-stages')) return;
    const r = el.getBoundingClientRect();
    if (r.width > 40) widest = Math.max(widest, r.right);
  });
  const sel = document.querySelector('.mapgrid select');
  const rail = document.querySelector('.rail');
  const railBg = rail ? getComputedStyle(rail).backgroundColor : '';
  return {
    railOpaque: !!railBg && railBg !== 'rgba(0, 0, 0, 0)' && railBg !== 'transparent',
    overflow: document.documentElement.scrollWidth - vw,
    widest: Math.round(widest - vw),
    selectWidth: sel ? Math.round(sel.getBoundingClientRect().width) : null,
  };
}"""

SCREENS = ["check", "sources", "schema", "prepare", "map", "programs", "run",
           "review", "queue", "summary", "export"]
WIDTHS = [1920, 1366, 1200, 1024, 768]


async def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "crosswalk_server:api",
         "--host", "127.0.0.1", "--port", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE + "/api/alive", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        post("/api/reset", {})
        post("/api/sources/example", {})
        post("/api/mode", {"mode": "Advanced"})
        sch = json.loads(urllib.request.urlopen(
            BASE + "/api/ui?screen=schema").read())["schema"]["fields"]
        for f in sch:
            if f.get("role") == "Client_ID":
                f["required"] = False
        post("/api/schema", {"schema": sch})
        post("/api/run/start", {"require_geocode": False, "jitter": True,
                                "seed": 1337})
        for _ in range(100):
            st = json.loads(urllib.request.urlopen(
                BASE + "/api/run/status").read())
            if st["state"] != "running":
                break
            time.sleep(0.1)
        for g in json.loads(urllib.request.urlopen(
                BASE + "/api/ui?screen=review").read())["review"]["groups"]:
            post("/api/review/group", {"gid": g["id"], "decision": "sent"})

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # paging a wide grid keeps its scroll position, on both axes
            import csv as _csv, io as _io
            _wb = _io.StringIO()
            _ww = _csv.writer(_wb)
            _ww.writerow(["client_id", "first_name", "last_name", "address_1", "city",
                          "state", "zip", "program"] + [f"extra_column_{i}" for i in range(14)])
            for i in range(80):
                _ww.writerow([str(i), "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY",
                              "11201", "Youth"] + [f"value {i}-{j}" for j in range(14)])
            import urllib.request as _ur
            _boundary = "----cwtest"
            _body = (f"--{_boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
                     f"filename=\"wide.csv\"\r\nContent-Type: text/csv\r\n\r\n"
                     + _wb.getvalue() + f"\r\n--{_boundary}--\r\n").encode()
            _req = _ur.Request(BASE + "/api/sources/upload", data=_body, method="POST",
                               headers={"Content-Type": f"multipart/form-data; boundary={_boundary}"})
            _ur.urlopen(_req)
            page = await browser.new_page(viewport={"width": 1300, "height": 900})
            await page.goto(BASE + "/")
            await page.wait_for_timeout(600)
            await page.evaluate("() => { UI.screen='sources'; load('sources'); }")
            await page.wait_for_timeout(900)
            await page.mouse.move(700, 500)
            if await page.locator("[data-table-preview]").count():
                await page.locator("[data-table-preview]").last.click()
                await page.wait_for_timeout(900)
                g = page.locator(".pvscroll[data-scrollkey]").first
                if await g.count() and await page.locator("[data-ppage='next']").count():
                    await g.evaluate("el => { el.scrollLeft = 300; }")
                    # bring the Next button into view the way a person would,
                    # then note where the page sits before the click
                    await page.locator("[data-ppage='next']").first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(150)
                    y0 = await page.evaluate("() => window.scrollY")
                    await page.locator("[data-ppage='next']").first.click()
                    await page.wait_for_timeout(900)
                    x = await page.locator(".pvscroll[data-scrollkey]").first.evaluate("el => el.scrollLeft")
                    y = await page.evaluate("() => window.scrollY")
                    check("paging a grid keeps its horizontal scroll position", x == 300)
                    check("paging a grid keeps the page's vertical position", abs(y - y0) < 5)
            await page.close()

            for w in WIDTHS:
                page = await browser.new_page(viewport={"width": w, "height": 1000})
                await page.goto(BASE + "/")
                await page.wait_for_timeout(600)
                for s in SCREENS:
                    await page.evaluate(f"() => {{ UI.screen='{s}'; load('{s}'); }}")
                    await page.wait_for_timeout(700)
                    if s == "review" and await page.locator("[data-preview]").count():
                        await page.locator("[data-preview]").first.click()
                        await page.wait_for_timeout(700)
                    r = await page.evaluate(FIND)
                    check(f"{s} at {w}px does not scroll the page sideways",
                          r["overflow"] <= 0)
                    check(f"{s} at {w}px keeps every element on screen",
                          r["widest"] <= 1)
                    if s == "check" and w >= 981:
                        check(f"the menu has its own background at {w}px, so it "
                              "is solid when it opens over the content",
                              r["railOpaque"])
                    if s == "map" and r["selectWidth"]:
                        check(f"map dropdowns at {w}px are sized to their "
                              "contents, not the screen",
                              120 <= r["selectWidth"] <= 420)
                await page.close()
            await browser.close()
    finally:
        server.terminate()


asyncio.run(main())
failed = [l for l, ok in results if not ok]
for l in failed:
    print(f"  [FAIL] {l}")
ok = not failed
print(f"LAYOUT TESTS: {'PASS' if ok else 'FAIL'} "
      f"({len(results) - len(failed)}/{len(results)})")
sys.exit(0 if ok else 1)
