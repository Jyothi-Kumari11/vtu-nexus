"""
VTU Nexus - Scraper Engine (runs in background thread for Flask dashboard)
"""
import os, re, sys, time, logging
import cv2, pytesseract
import pandas as pd
from collections import Counter
from threading import Thread, Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

VTU_URL      = "https://results.vtu.ac.in/D25J26Ecbcs/index.php"
INPUT_FILE   = "usn_list.xlsx"
RAW_OUTPUT   = "results_output.xlsx"
CAPTCHA_IMG  = "captcha.png"
SEM_DIGIT    = '3'
_OCR_CFG     = r"--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

log = logging.getLogger("vtu.scraper")

# ── shared state ──────────────────────────────────────────────
status = {
    "running": False, "done": False, "error": None,
    "total": 0, "processed": 0, "skipped": 0,
    "current_usn": "", "feed": [],
    "pass_count": 0, "fail_count": 0,
}
_stop_event = Event()


def _push(msg, level="INFO"):
    entry = {"time": time.strftime("%H:%M:%S"), "msg": msg, "level": level}
    status["feed"].append(entry)
    if len(status["feed"]) > 300:
        status["feed"].pop(0)
    getattr(log, level.lower(), log.info)(msg)


def _clean(t):
    return re.sub(r'[^A-Za-z0-9]', '', t).strip()


def solve_captcha(path):
    img = cv2.imread(path)
    if img is None: return ""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cands = []
    procs = [
        lambda g: cv2.threshold(g, 127, 255, cv2.THRESH_BINARY)[1],
        lambda g: cv2.threshold(g, 0,   255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        lambda g: cv2.adaptiveThreshold(
            cv2.fastNlMeansDenoising(cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), h=15),
            255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        lambda g: cv2.threshold(cv2.medianBlur(g, 3), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
    ]
    for p in procs:
        try:
            t = _clean(pytesseract.image_to_string(p(g), config=_OCR_CFG))
            if 3 <= len(t) <= 8: cands.append(t)
        except: pass
    if not cands:
        return _clean(pytesseract.image_to_string(g, config=_OCR_CFG))
    return Counter(cands).most_common(1)[0][0]


def _start_browser():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = webdriver.Chrome(options=opts)
    d.maximize_window()
    return d


SUBJ_RE = re.compile(
    r'([A-Z]{2,6}\d{3,4}[A-Z]?)\s+(.+?)\s+'
    r'(\d{1,3}|AB|ABS)\s+(\d{1,3}|AB|ABS)\s+(\d{1,3}|AB|ABS)\s+'
    r'([A-Z]{1,4})\s+(\d{4}-\d{2}-\d{2})'
)


def _scrape_worker():
    global status
    status.update(running=True, done=False, error=None,
                  processed=0, skipped=0, feed=[], pass_count=0, fail_count=0)
    _stop_event.clear()

    try:
        df_usn = pd.read_excel(INPUT_FILE)
        usn_list = df_usn.iloc[:, 0].dropna().astype(str).str.strip().tolist()
        status["total"] = len(usn_list)
        _push(f"Loaded {len(usn_list)} USNs from {INPUT_FILE}")

        all_results = []
        existing_usns = set()
        if os.path.exists(RAW_OUTPUT):
            try:
                old = pd.read_excel(RAW_OUTPUT)
                all_results = old.to_dict('records')
                existing_usns = set(old["USN"].astype(str).str.strip())
                _push(f"Cache: {len(existing_usns)} USNs already done — skipping them")
            except Exception as e:
                _push(f"Cache load failed: {e}", "WARNING")

        driver = _start_browser()
        _push("Browser started ✓")

        for idx, usn in enumerate(usn_list, 1):
            if _stop_event.is_set():
                _push("Stop requested — halting.", "WARNING")
                break

            status["current_usn"] = usn
            status["processed"] = idx

            if usn in existing_usns:
                status["skipped"] += 1
                _push(f"[{idx}/{len(usn_list)}] {usn} — SKIPPED (cached)")
                continue

            _push(f"[{idx}/{len(usn_list)}] Processing: {usn}")
            retry = 0

            while not _stop_event.is_set():
                try:
                    driver.get(VTU_URL)
                    usn_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "lns")))
                    usn_box.clear(); usn_box.send_keys(usn)

                    cap_el = driver.find_element(By.XPATH, "//img[contains(@src,'captcha')]")
                    cap_el.screenshot(CAPTCHA_IMG)
                    cap_txt = solve_captcha(CAPTCHA_IMG)
                    _push(f"  CAPTCHA: {cap_txt}")

                    driver.find_element(By.NAME, "captchacode").send_keys(cap_txt)
                    driver.find_element(By.XPATH, "//input[@type='submit']").click()

                    try:
                        alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
                        msg = alert.text.lower(); alert.accept()
                        if "captcha" in msg:
                            _push("  Wrong CAPTCHA, retrying…", "WARNING")
                            retry += 1; time.sleep(1); continue
                        else:
                            _push(f"  {usn} — no data on VTU portal. Skipping.", "WARNING")
                            break
                    except TimeoutException:
                        pass

                    body = driver.find_element(By.TAG_NAME, "body").text
                    if "Semester" not in body:
                        retry += 1; time.sleep(2); continue

                    name = sem = "Unknown"
                    for line in body.split("\n"):
                        if "Student Name" in line: name = line.split(":")[-1].strip()
                        if "Semester"     in line: sem  = line.split(":")[-1].strip()

                    seen = set(); added = 0
                    for m in SUBJ_RE.findall(body):
                        code = m[0]
                        if code in seen: continue
                        d = re.search(r'\d', code)
                        if d and d.group() != SEM_DIGIT: continue
                        seen.add(code); added += 1
                        all_results.append({
                            "USN": usn, "Name": name, "Semester": sem,
                            "SUBJECT CODE": code,
                            "SUBJECT NAME": " ".join(m[1].split()),
                            "INTERNAL MARKS": m[2], "EXTERNAL MARKS": m[3],
                            "TOTAL": m[4], "RESULT": m[5], "DATE": m[6]
                        })

                    _push(f"  ✓ {name} — {added} subjects extracted")
                    break

                except Exception as e:
                    retry += 1
                    err = str(e)[:120]
                    _push(f"  Attempt {retry} failed: {err}", "WARNING")
                    if any(x in err.lower() for x in ["disconnected","session","refused","connection"]):
                        _push("  Restarting browser…")
                        try: driver.quit()
                        except: pass
                        time.sleep(3)
                        driver = _start_browser()
                    else:
                        time.sleep(2)

        try: driver.quit()
        except: pass
        _push("Browser closed.")

        raw_df = pd.DataFrame(all_results).dropna(how='all')
        raw_df.to_excel(RAW_OUTPUT, index=False)
        _push(f"Raw data saved → {RAW_OUTPUT} ({len(raw_df)} rows)")

        # quick pass/fail count
        if not raw_df.empty and "RESULT" in raw_df.columns:
            p = (raw_df["RESULT"].astype(str).str.strip().str.upper() == "P")
            # count per unique USN
            pass_usns = raw_df[p]["USN"].nunique()
            status["pass_count"] = int(pass_usns)
            status["fail_count"] = int(raw_df["USN"].nunique() - pass_usns)

        _push("✅ Scraping complete! Run report generation to get Excel files.")
        status["done"] = True

    except Exception as e:
        status["error"] = str(e)
        _push(f"FATAL: {e}", "ERROR")
    finally:
        status["running"] = False


def start_scraping():
    if status["running"]:
        return False
    t = Thread(target=_scrape_worker, daemon=True)
    t.start()
    return True


def stop_scraping():
    _stop_event.set()


def get_status():
    return dict(status)
