"""Headless test of explorer/trace_explorer.html with Playwright (skipped when playwright/chromium is unavailable).
Checks: page loads with no console errors and no network request other than the file itself; the JS CPA agrees with a numpy CPA computed from the
same embedded data; the three modes behave as the labs say; screenshots are written to tests/screens/.
Run:  python tests/test_explorer.py"""
import os, sys, json, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import numpy as np
from rtlseclab.core.leakage import HW, stage1_scores

HTML = os.path.join(ROOT, "explorer", "trace_explorer.html")
SHOTS = os.path.join(ROOT, "tests", "screens")


def embedded():
    s = open(HTML).read()
    return json.loads(re.search(r"const D=(\{.*?\});\nconst HW", s, re.S).group(1))


def np_best(D, N, sigma, byte, mode):
    m = np.array(D["m"], dtype=np.uint8).reshape(-1, 8)[:N]; r = np.array(D["r"], dtype=np.uint8).reshape(-1, 8)[:N]
    z = np.array(D["z"]).reshape(-1, 3, 8)[:N]; k1 = np.array(D["k1"], dtype=np.uint8); c3 = np.array(D["c3"], dtype=np.uint8)
    v = m ^ k1 ^ c3
    if mode == "u":
        x = HW[v][:, byte] + sigma * z[:, 0, byte]; sc = stage1_scores(x, m, byte)
    else:
        a = HW[v ^ r][:, byte] + sigma * z[:, 1, byte]; c = HW[r][:, byte] + sigma * z[:, 2, byte]
        x = a if mode == "f" else (a - a.mean()) * (c - c.mean()); sc = stage1_scores(x, m, byte); sc = sc if mode == "f" else -sc
    return int(np.argmax(sc)), float(sc.max())


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: playwright not installed"); return 0
    os.makedirs(SHOTS, exist_ok=True); D = embedded(); fails = 0
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1000, "height": 900})
        errs, reqs = [], []
        pg.on("console", lambda msg: errs.append(msg.text) if msg.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda rq: reqs.append(rq.url))
        pg.goto("file://" + HTML)
        cases = [("u", 300, 2.0, 0, "01_unmasked"), ("f", 3000, 2.0, 0, "02_masked_first_order"), ("s", 3000, 2.0, 0, "03_masked_second_order"), ("u", 40, 4.0, 3, "04_unmasked_too_few")]
        for mode, N, sg, byte, name in cases:
            pg.select_option("#mode", mode); pg.select_option("#B", str(byte))
            pg.eval_on_selector("#N", "(e,v)=>{e.value=v;e.dispatchEvent(new Event('input'))}", N)
            pg.eval_on_selector("#S", "(e,v)=>{e.value=v;e.dispatchEvent(new Event('input'))}", sg)
            txt = pg.inner_text("#res"); js_ok = txt.startswith("Key byte recovered")
            m = re.search(r"best guess 0x([0-9a-f]{2}) \(r=(-?[0-9.]+)\)", txt); js_best, js_r = int(m.group(1), 16), float(m.group(2))
            n_best, n_r = np_best(D, N, sg, byte, mode)
            agree = js_best == n_best and abs(js_r - n_r) < 1e-3
            truth = D["k1"][byte] == js_best
            print("%-26s JS: %-42s numpy best 0x%02x r=%.3f  agree=%s" % (name, txt[:42], n_best, n_r, agree))
            if not agree or js_ok != truth: fails += 1
            pg.screenshot(path=os.path.join(SHOTS, name + ".png"))
        exp = {"01_unmasked": True, "02_masked_first_order": False, "03_masked_second_order": True}
        pg.select_option("#mode", "u"); pg.select_option("#B", "0")
        pg.eval_on_selector("#N", "(e,v)=>{e.value=v;e.dispatchEvent(new Event('input'))}", 300); pg.eval_on_selector("#S", "(e,v)=>{e.value=v;e.dispatchEvent(new Event('input'))}", 2)
        if not pg.inner_text("#res").startswith("Key byte recovered"): print("FAIL unmasked N=300 sigma=2 should recover byte 0"); fails += 1
        pg.set_viewport_size({"width": 390, "height": 900}); pg.screenshot(path=os.path.join(SHOTS, "05_phone_width.png"), full_page=True)
        ext = [u for u in reqs if not u.startswith("file://")]
        if ext: print("FAIL external requests:", ext); fails += 1
        if errs: print("FAIL console errors:", errs); fails += 1
        sw = pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        if not sw: print("FAIL horizontal scroll at 390 px"); fails += 1
        br.close()
    print("EXPLORER TEST:", "PASS" if not fails else "FAIL (%d)" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
