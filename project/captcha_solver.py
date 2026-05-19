"""
VTU CAPTCHA Solver - Multi-Strategy OCR
"""
import cv2
import pytesseract
import numpy as np
import re
from collections import Counter

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
CFG = r"--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def _clean(text):
    return re.sub(r'[^A-Za-z0-9]', '', text).strip()

def solve_captcha(image_path: str) -> str:
    img = cv2.imread(image_path)
    if img is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    results = []

    # Strategy 1: Simple threshold
    _, t1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    r1 = _clean(pytesseract.image_to_string(t1, config=CFG))
    if 3 <= len(r1) <= 8: results.append(r1)

    # Strategy 2: Otsu
    _, t2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    r2 = _clean(pytesseract.image_to_string(t2, config=CFG))
    if 3 <= len(r2) <= 8: results.append(r2)

    # Strategy 3: Upscale + denoise + adaptive
    up = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    dn = cv2.fastNlMeansDenoising(up, h=15)
    t3 = cv2.adaptiveThreshold(dn, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    r3 = _clean(pytesseract.image_to_string(t3, config=CFG))
    if 3 <= len(r3) <= 8: results.append(r3)

    # Strategy 4: Median blur + Otsu
    bl = cv2.medianBlur(gray, 3)
    _, t4 = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    r4 = _clean(pytesseract.image_to_string(t4, config=CFG))
    if 3 <= len(r4) <= 8: results.append(r4)

    if not results:
        return _clean(pytesseract.image_to_string(gray, config=CFG))

    best, _ = Counter(results).most_common(1)[0]
    return best
