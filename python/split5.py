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

2) QR detection (identical strategy to clean5.py):
   - Decoder is ZBar via pyzbar, restricted to QR symbols. OpenCV's QRCodeDetector
     is NOT used: it is measurably weaker on small/low-contrast/warped codes, which
     produced pages that clean5.py accepted but split4.py could not decode.
   - The FULL page is rendered at --dpi (default 250), exactly as clean5.py does,
     instead of only a footer strip. So split5 sees precisely what clean5 saw.
   - Robustness variants: grayscale + autocontrast, several downscales, inverted,
     and a threshold sweep (plain and inverted), keeping the best variant.
   - Early exit once 2 QR codes are found (the expected P/S pair).
   - P and S are assigned by payload content (P<digits> / S<digits>), not by
     position, so left/right cropping is unnecessary.

3) Parallelization:
   - One task per page, each in its own process (as in clean5.py).
   - Each worker opens the PDF independently (safe with PyMuPDF).
   - Crash isolation: ZBar is native code and can abort its process. One task per
     page means such an abort costs exactly that page, which is then reported as
     undecodable; the run continues.
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
  brew install zbar
  pip install pymupdf pillow pyzbar reportlab

"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageOps
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


def render_page_to_pil(pdf_path: str, page_index: int, dpi: int) -> Image.Image:
  """
  Rasterize one PDF page into a Pillow Image.

  Identical to clean5.py:
    - The FULL page is rendered, not a footer strip, so a QR that sits outside
      the footer band is still seen.
    - PDFs use 72 points/inch, so rendering at dpi means scaling by dpi/72.
    - We reopen the document here (per worker) to keep worker tasks independent.
  """
  doc = fitz.open(pdf_path)
  try:
    page = doc.load_page(page_index)

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img
  finally:
    doc.close()


def _symbol_payload(data) -> str:
  """
  Convert a ZBar symbol payload (bytes) into a printable string.

  Notes:
    - pyzbar returns raw bytes; QR content is usually UTF-8 but not guaranteed.
    - Undecodable bytes are replaced instead of raising.
    - Whitespace is collapsed, which the P_RE / S_RE patterns tolerate.
  """
  if isinstance(data, bytes):
    text = data.decode("utf-8", errors="replace")
  else:
    text = str(data)
  return " ".join(text.split())


def _dedup_detections(decoded) -> List[Tuple[Tuple[int, int, int, int], str]]:
  """
  Deduplicate QR detections by bounding box, keeping the decoded payload.

  Why:
    - ZBar may report the same QR multiple times depending on decoding pass.
    - We only care about distinct QR blocks on the page.

  Returns:
    - Sorted list of ((left, top, width, height), payload) pairs.
  """
  by_box: Dict[Tuple[int, int, int, int], str] = {}
  for sym in decoded:
    r = sym.rect
    box = (int(r.left), int(r.top), int(r.width), int(r.height))
    by_box.setdefault(box, _symbol_payload(sym.data))
  return sorted(by_box.items())


def decode_qr_with_variants(img_rgb: Image.Image) -> dict:
  """
  Decode QR codes using multiple image variants for robustness.

  This is the decoding strategy of clean5.py, unchanged, so that a page which
  clean5.py classified as conformant decodes here as well.

  Returns:
    {
      "count": int,                     # max deduplicated QR count found
      "boxes": list[(l,t,w,h)],         # bounding boxes for the best variant
      "values": list[str],              # decoded payloads, aligned with "boxes"
      "img_h": int, "img_w": int        # dimensions of the variant image
    }

  Robustness strategy:
    - Convert to grayscale + autocontrast (stabilizes lighting differences).
    - Try several downscales (sometimes decoding works better when noise is reduced).
    - Try inverted (black/white reversal).
    - Try thresholded (binarized) images at several cutoffs, plus inverted threshold.

  Selection rule:
    - Keep the variant that yields the maximum number of distinct QR boxes.

  Performance shortcut:
    - Early stop once we reach 2 QR codes, which is the expected P/S pair.
  """
  from pyzbar.pyzbar import decode, ZBarSymbol

  # Normalize input to grayscale and improve contrast.
  base = ImageOps.autocontrast(img_rgb.convert("L"))

  best_count = 0
  best_dets: List[Tuple[Tuple[int, int, int, int], str]] = []
  best_h = base.height
  best_w = base.width

  # Scale list: attempt slight downscales to reduce noise / aliasing.
  scales = [1.0, 0.85, 0.7, 0.5]

  # Threshold sweep: fallback for poor contrast prints/scans.
  thresholds = (80, 100, 120, 140, 160)

  def consider(im: Image.Image) -> None:
    nonlocal best_count, best_dets, best_h, best_w

    # Restrict decoder to QR only:
    # - reduces accidental decodes of other symbologies
    # - can help reduce ZBar instability in some cases
    decoded = decode(im, symbols=[ZBarSymbol.QRCODE])

    dets = _dedup_detections(decoded)
    c = len(dets)

    # Keep the best observed variant.
    if c > best_count:
      best_count = c
      best_dets = dets
      best_h = im.height
      best_w = im.width

  for s in scales:
    if s != 1.0:
      w = max(1, int(base.width * s))
      h = max(1, int(base.height * s))
      im = base.resize((w, h), resample=Image.Resampling.LANCZOS)
    else:
      im = base

    # Variant 1: plain grayscale autocontrast
    consider(im)
    if best_count >= 2:
      break

    # Variant 2: inverted grayscale
    inv = ImageOps.invert(im)
    consider(inv)
    if best_count >= 2:
      break

    # Variant 3/4: threshold sweep (binary) and inverted binary
    for t in thresholds:
      bw = im.point(lambda p: 255 if p > t else 0, mode="L")
      consider(bw)
      if best_count >= 2:
        break

      bw_inv = ImageOps.invert(bw)
      consider(bw_inv)
      if best_count >= 2:
        break

    if best_count >= 2:
      break

  return {
    "count": best_count,
    "boxes": [box for box, _ in best_dets],
    "values": [value for _, value in best_dets],
    "img_h": best_h,
    "img_w": best_w
  }


def parse_code(text: str, pat: "re.Pattern") -> Optional[int]:
  """
  Extract the integer from a "P<digits>" / "S<digits>" payload.
  """
  m = pat.match(text or "")
  if not m:
    return None
  try:
    return int(m.group(1))
  except Exception:
    return None


def decode_p_s_from_page(img: Image.Image) -> Tuple[Optional[int], Optional[int], List[str], List[str]]:
  """
  Decode the whole page with the clean5.py variant strategy and pick out P and S.

  Assignment is by payload content, not by geometry: the left QR carries P<n>
  and the right one S<n>, so the regexes decide which is which. That also means
  a page whose QRs are not exactly where we expect still resolves correctly.

  Returns (p_num, s_num, decoded_texts, issues)
  """
  issues: List[str] = []

  res = decode_qr_with_variants(img)
  decoded_texts: List[str] = list(dict.fromkeys(res["values"]))

  p_num: Optional[int] = None
  s_num: Optional[int] = None

  for t in decoded_texts:
    if p_num is None:
      pv = parse_code(t, P_RE)
      if pv is not None:
        p_num = pv
        continue
    if s_num is None:
      sv = parse_code(t, S_RE)
      if sv is not None:
        s_num = sv

  if not decoded_texts:
    issues.append("Failed to decode any QR code on this page.")
  elif p_num is None or s_num is None:
    issues.append(f"Decoded {len(decoded_texts)} QR code(s), but not a complete P/S pair: {decoded_texts}")

  return p_num, s_num, decoded_texts, issues


def _scan_worker(args: Tuple[str, int, int]) -> PageResult:
  """
  Worker: scan exactly one page in its own process (as clean5.py does).

  Why one page per task:
    - ZBar is native code and can abort the whole process on an assertion
      failure. With one page per task, such a crash costs that single page;
      the main process notices the dead future and continues.
    - Any ordinary exception is caught here and turned into an issue, so a
      single bad page never aborts the run.
  """
  input_path, page_index, dpi = args

  issues: List[str] = []

  try:
    img = render_page_to_pil(input_path, page_index, dpi=dpi)
  except Exception as ex:
    issues.append(mark(True, f"Failed to render page: {ex}"))
    return PageResult(page_index=page_index, p_num=None, s_num=None, raw_texts=[], issues=issues)

  try:
    p_num, s_num, raw, dec_issues = decode_p_s_from_page(img)
  except Exception:
    issues.append(mark(True, f"Decoder error: {traceback.format_exc(limit=1).strip()}"))
    return PageResult(page_index=page_index, p_num=None, s_num=None, raw_texts=[], issues=issues)

  for msg in dec_issues:
    issues.append(mark(True, msg))

  if p_num is None:
    issues.append(mark(True, "Missing/undecodable P-number for this page."))
  if s_num is None:
    issues.append(mark(True, "Missing/undecodable S-number for this page."))

  return PageResult(page_index=page_index, p_num=p_num, s_num=s_num, raw_texts=raw, issues=issues)


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
  dpi: int,
  workers: int
) -> Tuple[int, List[PageResult]]:
  """
  Parallel scan, one task per page. Returns (page_count, results).
  """
  # Read page count once in main process.
  doc = fitz.open(input_path)
  n = doc.page_count
  doc.close()

  log(f"[scan] Input: {input_path}")
  log(f"[scan] Pages: {n}")
  log(f"[scan] dpi={dpi}, workers={workers}")
  log(f"[scan] decoder: ZBar via pyzbar, QR only, clean5.py variant strategy")

  results: List[PageResult] = []

  with ProcessPoolExecutor(max_workers=workers) as ex:
    futures = {ex.submit(_scan_worker, (input_path, i, dpi)): i for i in range(n)}

    done_pages = 0
    for fut in as_completed(futures):
      i = futures[fut]

      # A native ZBar abort kills the worker; fut.result() then raises here.
      try:
        r = fut.result()
      except Exception as ex_worker:
        r = PageResult(
          page_index=i,
          p_num=None,
          s_num=None,
          raw_texts=[],
          issues=[mark(True, f"Worker crashed on this page ({type(ex_worker).__name__}); page not decoded.")]
        )

      results.append(r)
      # Continuous reporting per page result (may arrive out of order)
      done_pages += 1
###      log(f"[scan] Page {r.page_index + 1}/{n} done.")
      if r.issues:
        # Results arrive out of order, so name the page in every issue line.
        for msg in r.issues:
          log(f"[scan]   page {r.page_index + 1}: {msg}")
        if r.raw_texts:
          log(f"[scan]   page {r.page_index + 1}: decoded texts: {r.raw_texts}")

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
  ap.add_argument("--dpi", type=int, default=250,
                  help="Render DPI for decoding (default: 250, same as clean5.py).")
  ap.add_argument("--workers", type=int, default=os.cpu_count() or 4,
                  help="Number of worker processes for parallel scanning (default: CPU count).")

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
  dpi = max(1, int(args.dpi))

  try:
    _, results = scan_pdf_parallel(
      input_path=input_path,
      dpi=dpi,
      workers=workers
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