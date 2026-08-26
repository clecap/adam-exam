#!/usr/bin/env python3
"""
Split a multi-page PDF into per-serial PDFs based on two QR codes in each page footer:

- Left QR:  "P<digits>"  => QR-page-number
- Right QR: "S<digits>"  => QR-serial-number

Output for each serial S:
- File name: "ssss.pdf" where ssss is 4-digit zero-padded serial number
- Pages ordered by QR-page-number P1, P2, ...
- Missing P in the sequence -> insert placeholder page: "missing page with page number p"

Requested adaptations implemented:

1) Duplicates:
   - If (serial, P) occurs multiple times, include it ONLY ONCE (first occurrence by source page index).
   - Report duplicates with "******".

2) Faster QR detection:
   - Lighter-weight decode: fewer preprocessing variants, early exit.
   - Decodes left-half and right-half regions separately (reduces confusion, faster).
   - Uses grayscale + optional CLAHE + (optionally) Otsu/invert as fallback.

3) Parallelization:
   - Page scanning is parallelized across multiple processes.
   - Each worker opens the PDF independently (safe with PyMuPDF).
   - Main process merges results deterministically and ensures data integrity.
   - Continuous reporting: progress messages appear as worker results complete (may be out of order; page indices shown).

4) Expected page count per file:
   - You can set a global expected page count for ALL serials: --expected-pages N
   - Or provide a CSV mapping: --expected-map /path/to/map.csv
     CSV format: serial,expected_pages
     Example:
       12,24
       13,24
   - If expected is set for a serial:
     - Output will contain EXACTLY pages P1..Pexpected (placeholders inserted as needed).
     - Any source pages with P > expected are ignored and reported with "******".
     - If the serial has fewer actual pages than expected, placeholders are added and a file-level report is emitted.

5) Reporting:
   - Extraordinary situations (duplicates, placeholders, failed QR detections, ignored out-of-range pages) are marked with "******".
   - During writing: only placeholder generation is reported (plus file start/end and extraordinary notes).

Dependencies:
  pip install pymupdf opencv-python reportlab

"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import numpy as np
import cv2
from reportlab.pdfgen import canvas

from concurrent.futures import ProcessPoolExecutor, as_completed


P_RE = re.compile(r"^\s*P(\d+)\s*$", re.IGNORECASE)
S_RE = re.compile(r"^\s*S(\d+)\s*$", re.IGNORECASE)


@dataclass
class PageResult:
  page_index: int
  p_num: Optional[int]
  s_num: Optional[int]
  raw_texts: List[str]
  issues: List[str]


def log(msg: str) -> None:
  print(msg, flush=True)


def mark(extraordinary: bool, msg: str) -> str:
  return f"****** {msg}" if extraordinary else msg


def render_footer_bgr(doc: fitz.Document, page_index: int, footer_height_pts: float, zoom: float) -> np.ndarray:
  page = doc.load_page(page_index)
  rect = page.rect
  footer = fitz.Rect(rect.x0, max(rect.y1 - footer_height_pts, rect.y0), rect.x1, rect.y1)
  mat = fitz.Matrix(zoom, zoom)
  pix = page.get_pixmap(matrix=mat, clip=footer, alpha=False)
  img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
  if pix.n == 3:
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
  if pix.n == 4:
    return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
  return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _try_decode(detector: cv2.QRCodeDetector, bgr: np.ndarray) -> List[str]:
  texts: List[str] = []

  ok, t_multi, _, _ = detector.detectAndDecodeMulti(bgr)
  if ok and t_multi is not None:
    for t in t_multi:
      if t:
        t = t.strip()
        if t:
          texts.append(t)

  if not texts:
    t_single, _, _ = detector.detectAndDecode(bgr)
    if t_single:
      t_single = t_single.strip()
      if t_single:
        texts.append(t_single)

  return texts


def _preprocess_light(gray: np.ndarray, use_clahe: bool, add_otsu: bool) -> List[np.ndarray]:
  variants: List[np.ndarray] = []

  g = gray
  variants.append(g)

  if use_clahe:
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    variants.append(clahe.apply(g))

  if add_otsu:
    _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)
    variants.append(255 - otsu)

  return variants


def decode_p_s_from_footer(bgr: np.ndarray, use_clahe: bool, add_otsu: bool) -> Tuple[Optional[int], Optional[int], List[str], List[str]]:
  """
  Lightweight but robust-ish decoding:
  - Split into left/right halves.
  - Try a small set of preprocess variants.
  - Early exit when P and S both found.
  Returns (p_num, s_num, decoded_texts, issues)
  """
  issues: List[str] = []
  decoded_texts: List[str] = []
  detector = cv2.QRCodeDetector()

  h, w = bgr.shape[:2]
  left = bgr[:, : max(1, w // 2)]
  right = bgr[:, max(0, w // 2):]

  def parse_code(text: str, pat: re.Pattern) -> Optional[int]:
    m = pat.match(text or "")
    if not m:
      return None
    try:
      return int(m.group(1))
    except Exception:
      return None

  p_num: Optional[int] = None
  s_num: Optional[int] = None

  # Decode right first (often the problematic one): focus effort there slightly.
  for region_name, region in [("right", right), ("left", left)]:
    if (region_name == "right" and s_num is not None) or (region_name == "left" and p_num is not None):
      continue

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    variants = _preprocess_light(gray, use_clahe=use_clahe, add_otsu=add_otsu)

    found_any = False
    for v in variants:
      bgr_v = cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)
      texts = _try_decode(detector, bgr_v)
      if texts:
        found_any = True
        for t in texts:
          decoded_texts.append(t)
          if p_num is None:
            pv = parse_code(t, P_RE)
            if pv is not None:
              p_num = pv
          if s_num is None:
            sv = parse_code(t, S_RE)
            if sv is not None:
              s_num = sv
        if p_num is not None and s_num is not None:
          return p_num, s_num, list(dict.fromkeys(decoded_texts)), issues

    if not found_any:
      issues.append(f"Failed to decode any QR in {region_name} region.")

  return p_num, s_num, list(dict.fromkeys(decoded_texts)), issues


def _scan_worker(args: Tuple[str, List[int], float, float, bool, bool]) -> List[PageResult]:
  """
  Worker: open the PDF independently and scan assigned pages.
  """
  input_path, page_indices, footer_height_pts, zoom, use_clahe, add_otsu = args
  doc = fitz.open(input_path)
  out: List[PageResult] = []

  for i in page_indices:
    issues: List[str] = []
    raw: List[str] = []
    p_num: Optional[int] = None
    s_num: Optional[int] = None

    try:
      bgr = render_footer_bgr(doc, i, footer_height_pts=footer_height_pts, zoom=zoom)
    except Exception as ex:
      issues.append(mark(True, f"Failed to render footer: {ex}"))
      out.append(PageResult(page_index=i, p_num=None, s_num=None, raw_texts=[], issues=issues))
      continue

    p_num, s_num, raw, dec_issues = decode_p_s_from_footer(bgr, use_clahe=use_clahe, add_otsu=add_otsu)
    for msg in dec_issues:
      issues.append(mark(True, msg))

    if p_num is None:
      issues.append(mark(True, "Missing/undecodable P-number for this page."))
    if s_num is None:
      issues.append(mark(True, "Missing/undecodable S-number for this page."))

    out.append(PageResult(page_index=i, p_num=p_num, s_num=s_num, raw_texts=raw, issues=issues))

  doc.close()
  return out


def chunk_indices(n: int, chunks: int) -> List[List[int]]:
  chunks = max(1, chunks)
  buckets: List[List[int]] = [[] for _ in range(chunks)]
  for i in range(n):
    buckets[i % chunks].append(i)
  return [b for b in buckets if b]


def load_expected_map(path: str) -> Dict[int, int]:
  """
  CSV: serial,expected_pages
  """
  m: Dict[int, int] = {}
  with open(path, "r", newline="") as f:
    reader = csv.reader(f)
    for row in reader:
      if not row:
        continue
      if len(row) < 2:
        continue
      try:
        s = int(str(row[0]).strip())
        e = int(str(row[1]).strip())
        if e > 0:
          m[s] = e
      except Exception:
        continue
  return m


def build_placeholder_pdf_page(page_width_pts: float, page_height_pts: float, message: str) -> bytes:
  buf = io.BytesIO()
  c = canvas.Canvas(buf, pagesize=(page_width_pts, page_height_pts))
  c.setFont("Helvetica", 16)
  margin = 72
  c.drawString(margin, page_height_pts - margin, message)
  c.showPage()
  c.save()
  return buf.getvalue()


def scan_pdf_parallel(
  input_path: str,
  footer_height_pts: float,
  zoom: float,
  workers: int,
  use_clahe: bool,
  add_otsu: bool
) -> Tuple[int, List[PageResult]]:
  """
  Parallel scan. Returns (page_count, results).
  """
  # Read page count once in main process.
  doc = fitz.open(input_path)
  n = doc.page_count
  doc.close()

  log(f"[scan] Input: {input_path}")
  log(f"[scan] Pages: {n}")
  log(f"[scan] footer-height-pt={footer_height_pts}, zoom={zoom}, workers={workers}")
  log(f"[scan] decode options: clahe={use_clahe}, otsu_fallback={add_otsu}")

  buckets = chunk_indices(n, workers)
  results: List[PageResult] = []

  with ProcessPoolExecutor(max_workers=workers) as ex:
    futures = []
    for b in buckets:
      futures.append(ex.submit(_scan_worker, (input_path, b, footer_height_pts, zoom, use_clahe, add_otsu)))

    done_pages = 0
    for fut in as_completed(futures):
      batch = fut.result()
      results.extend(batch)
      # Continuous reporting per page result (may arrive out of order)
      for r in batch:
        done_pages += 1
###        log(f"[scan] Page {r.page_index + 1}/{n} done.")
        if r.issues:
          for msg in r.issues:
            log(f"[scan]   {msg}")
          if r.raw_texts:
            log(f"[scan]   decoded texts: {r.raw_texts}")

  # Ensure results are ordered by page index for deterministic merge.
  results.sort(key=lambda x: x.page_index)
  log(f"[scan] Done.")
  return n, results


def merge_results(
  results: List[PageResult],
  expected_global: Optional[int],
  expected_map: Dict[int, int]
) -> Tuple[Dict[int, Dict[int, int]], Dict[int, List[Tuple[int, int]]], List[Tuple[int, int, int]]]:
  """
  Build:
    serial_pages: serial -> (p_num -> page_index)  (dedup to first occurrence)
    duplicates: serial -> list of (p_num, duplicate_page_index)
    out_of_range: list of (serial, p_num, page_index) for p_num > expected (when expected is defined for that serial)
  """
  serial_pages: Dict[int, Dict[int, int]] = {}
  duplicates: Dict[int, List[Tuple[int, int]]] = {}
  out_of_range: List[Tuple[int, int, int]] = []

  def expected_for(serial: int) -> Optional[int]:
    if serial in expected_map:
      return expected_map[serial]
    return expected_global

  for r in results:
    if r.p_num is None or r.s_num is None:
      continue

    s = r.s_num
    p = r.p_num

    exp = expected_for(s)
    if exp is not None and p > exp:
      out_of_range.append((s, p, r.page_index))
      continue

    if s not in serial_pages:
      serial_pages[s] = {}
    if p in serial_pages[s]:
      # duplicate: keep first, report later
      if s not in duplicates:
        duplicates[s] = []
      duplicates[s].append((p, r.page_index))
      continue

    serial_pages[s][p] = r.page_index

  return serial_pages, duplicates, out_of_range


def write_outputs(
  input_path: str,
  serial_pages: Dict[int, Dict[int, int]],
  duplicates: Dict[int, List[Tuple[int, int]]],
  out_of_range: List[Tuple[int, int, int]],
  expected_global: Optional[int],
  expected_map: Dict[int, int]
) -> None:
  out_dir = os.path.dirname(os.path.abspath(input_path))
  base = os.path.basename(input_path)

  if not serial_pages:
    log(mark(True, "[write] No valid (P,S) pairs found. No output will be written."))
    return

  # Open source doc in main process only for writing/inserting.
  src_doc = fitz.open(input_path)

  # Placeholder page size from page 1.
  ref_page = src_doc.load_page(0)
  ref_rect = ref_page.rect
  page_w = float(ref_rect.width)
  page_h = float(ref_rect.height)

  def expected_for(serial: int) -> Optional[int]:
    if serial in expected_map:
      return expected_map[serial]
    return expected_global

  # Report duplicates and out-of-range now (extraordinary)
  if duplicates:
    for s in sorted(duplicates.keys()):
      items = duplicates[s]
      # Summarize by P
      by_p: Dict[int, List[int]] = {}
      for p, idx in items:
        by_p.setdefault(p, []).append(idx + 1)
      for p in sorted(by_p.keys()):
        log(mark(True, f"[scan] Duplicate for serial S{s}: P{p} also appears on source pages {by_p[p]} (ignored duplicates, kept first)."))

  if out_of_range:
    for s, p, idx in sorted(out_of_range, key=lambda x: (x[0], x[1], x[2])):
      exp = expected_for(s)
      log(mark(True, f"[scan] Ignored out-of-range page for serial S{s}: P{p} on source page {idx + 1} exceeds expected {exp}."))

  for s in sorted(serial_pages.keys()):
    p_map = serial_pages[s]
    exp = expected_for(s)

    if exp is not None:
      target_max = exp
      actual_max = max(p_map.keys()) if p_map else 0
      if actual_max < exp:
        log(mark(True, f"[write] Serial S{s}: has pages only up to P{actual_max}, expected P1..P{exp}. Placeholders will be added."))
    else:
      target_max = max(p_map.keys()) if p_map else 0

    if target_max <= 0:
      log(mark(True, f"[write] Skipping serial S{s}: no positive P-numbers found."))
      continue

    out_name = f"{s:04d}.pdf"
    out_path = os.path.join(out_dir, out_name)

###    log(f"[write] Serial S{s} -> {out_name} (from {base})")

    out_doc = fitz.open()

    for p in range(1, target_max + 1):
      if p not in p_map:
        msg = f"missing page with page number {p}"
        log(mark(True, f"[write] MISSING: serial S{s} placeholder for P{p}"))
        ph_bytes = build_placeholder_pdf_page(page_w, page_h, msg)
        ph_doc = fitz.open("pdf", ph_bytes)
        out_doc.insert_pdf(ph_doc, from_page=0, to_page=0)
        ph_doc.close()
      else:
        idx = p_map[p]
        out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)

    out_doc.save(out_path)
    out_doc.close()
###    log(f"[write] Wrote: {out_path}")

  src_doc.close()
  log("[write] All done.")


def main() -> int:
  ap = argparse.ArgumentParser(description="Split PDF into per-serial PDFs based on footer QR codes P# (left) and S# (right).")
  ap.add_argument("input_pdf", help="Path to the input PDF.")

  # Performance / decode tuning
  ap.add_argument("--footer-height-pt", type=float, default=160.0,
                  help="Footer strip height in PDF points to scan (default: 160). Increase if QRs sit higher.")
  ap.add_argument("--zoom", type=float, default=3.0,
                  help="Render zoom factor for the footer strip (default: 3.0). Increase if decoding fails.")
  ap.add_argument("--workers", type=int, default=os.cpu_count() or 4,
                  help="Number of worker processes for parallel scanning (default: CPU count).")
  ap.add_argument("--no-clahe", action="store_true",
                  help="Disable CLAHE contrast enhancement (faster, sometimes less robust).")
  ap.add_argument("--no-otsu", action="store_true",
                  help="Disable Otsu/invert fallback variants (faster, sometimes less robust).")

  # Expected pages
  ap.add_argument("--expected-pages", type=int, default=None,
                  help="Expected page count per output file (applies to all serials unless overridden by --expected-map).")
  ap.add_argument("--expected-map", type=str, default=None,
                  help="CSV mapping: serial,expected_pages (overrides --expected-pages for listed serials).")

  args = ap.parse_args()

  input_path = os.path.abspath(args.input_pdf)
  if not os.path.isfile(input_path):
    log(mark(True, f"ERROR: Input file not found: {input_path}"))
    return 2
  if not input_path.lower().endswith(".pdf"):
    log(mark(True, f"ERROR: Input must be a .pdf file: {input_path}"))
    return 2

  expected_global: Optional[int] = args.expected_pages
  if expected_global is not None and expected_global <= 0:
    log(mark(True, "ERROR: --expected-pages must be a positive integer."))
    return 2

  expected_map: Dict[int, int] = {}
  if args.expected_map:
    if not os.path.isfile(args.expected_map):
      log(mark(True, f"ERROR: expected-map file not found: {args.expected_map}"))
      return 2
    expected_map = load_expected_map(args.expected_map)

  workers = max(1, int(args.workers))
  use_clahe = not bool(args.no_clahe)
  add_otsu = not bool(args.no_otsu)

  try:
    _, results = scan_pdf_parallel(
      input_path=input_path,
      footer_height_pts=float(args.footer_height_pt),
      zoom=float(args.zoom),
      workers=workers,
      use_clahe=use_clahe,
      add_otsu=add_otsu
    )
  except Exception as ex:
    log(mark(True, f"ERROR during scanning: {ex}"))
    return 1

  serial_pages, duplicates, out_of_range = merge_results(
    results=results,
    expected_global=expected_global,
    expected_map=expected_map
  )

  try:
    write_outputs(
      input_path=input_path,
      serial_pages=serial_pages,
      duplicates=duplicates,
      out_of_range=out_of_range,
      expected_global=expected_global,
      expected_map=expected_map
    )
  except Exception as ex:
    log(mark(True, f"ERROR during writing outputs: {ex}"))
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())