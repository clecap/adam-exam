#!/usr/bin/env python3
"""
Scan a PDF where each page must contain exactly TWO QR code blocks.

High-level behavior:
  - Render each PDF page into a raster image at configurable DPI.
  - Detect QR codes (ZBar via pyzbar) with multiple robustness variants.
  - Classify pages:
      * conformant: exactly 2 QR codes
      * buggy: anything else (0, 1, 3, ...) or any decoding/worker failure
  - Orientation rule:
      * QR codes should end up in the footer in outputs
      * If QRs appear in the header, rotate that page by 180° in outputs
  - Produce two output PDFs:
      * conformant output: only conformant pages
      * buggy output: all other pages
  - Emit continuous progress to stdout and (optionally) write a final report file.

Concurrency & crash isolation:
  - QR decoding is run in separate OS processes using ProcessPoolExecutor.
    This mitigates hard crashes in ZBar native code (assert aborts) by confining
    the crash to the worker process instead of killing the main process.

Install (macOS):
  brew install zbar
  python3 -m pip install pymupdf pillow pyzbar
"""

import argparse
import atexit
import io
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

import fitz  # PyMuPDF: fast PDF rasterization + PDF rewriting
from PIL import Image, ImageOps


def render_page_to_pil(pdf_path: str, page_index: int, dpi: int) -> Image.Image:
  """
  Rasterize one PDF page into a Pillow Image.

  Notes:
    - QR detection operates on pixels, not PDF vector content.
    - DPI matters: too low -> missing modules; too high -> slower and more memory.
    - We reopen the document here (per worker) to keep worker tasks independent.
  """
  doc = fitz.open(pdf_path)
  try:
    page = doc.load_page(page_index)

    # PDFs use 72 points/inch. Rendering at dpi means scaling by dpi/72.
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    # Pixmap is the rendered raster buffer. alpha=False keeps it RGB (smaller).
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # Convert pixmap samples (bytes) into a Pillow RGB image.
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img
  finally:
    doc.close()


def _symbol_payload(data) -> str:
  """
  Convert a ZBar symbol payload (bytes) into a printable string.

  Notes:
    - pyzbar returns raw bytes; QR content is usually UTF-8 but not guaranteed.
    - Undecodable bytes are replaced instead of raising, because a weird payload
      must not turn an otherwise conformant page into a decoder error.
    - Newlines/tabs are collapsed so one page stays one console line.
  """
  if isinstance(data, bytes):
    text = data.decode("utf-8", errors="replace")
  else:
    text = str(data)
  return " ".join(text.split())


def _dedup_detections(decoded) -> list[tuple[tuple[int, int, int, int], str]]:
  """
  Deduplicate QR detections by bounding box, keeping the decoded payload.

  Why:
    - ZBar may report the same QR multiple times depending on decoding pass.
    - We only care about distinct QR blocks on the page, but we also want to
      show what each block actually contains.

  Returns:
    - Sorted list of ((left, top, width, height), payload) pairs.
      Sorting by box gives a stable, geometry-based order (top-to-bottom,
      then left-to-right for equal tops).
  """
  by_box: dict[tuple[int, int, int, int], str] = {}
  for sym in decoded:
    r = sym.rect
    box = (int(r.left), int(r.top), int(r.width), int(r.height))
    # First payload wins: identical boxes are the same physical QR block.
    by_box.setdefault(box, _symbol_payload(sym.data))
  return sorted(by_box.items())


def _qr_in_header(boxes: list[tuple[int, int, int, int]], img_h: int) -> bool:
  """
  Decide whether detected QR codes are located in the header.

  Heuristic:
    - Compute the vertical center of each QR bounding box.
    - Average the centers.
    - If the average is in the top half of the image, treat as header.

  Rationale:
    - We only need a stable orientation decision (header vs footer),
      not precise geometry.
    - Rotating 180° moves header to footer and vice versa.
  """
  if not boxes or img_h <= 0:
    return False

  centers = []
  for left, top, w, h in boxes:
    centers.append(top + (h / 2.0))

  avg_cy = sum(centers) / len(centers)
  return avg_cy < (img_h * 0.5)


def decode_qr_with_variants(img_rgb: Image.Image) -> dict:
  """
  Decode QR codes using multiple image variants for robustness.

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
    - Early stop once we reach 2 QR codes (the target count) because
      finding "more" is not necessary for classification in this program.
      If you want to minimize false "OK" classifications, remove early stop.
  """
  from pyzbar.pyzbar import decode, ZBarSymbol

  # Normalize input to grayscale and improve contrast.
  base = ImageOps.autocontrast(img_rgb.convert("L"))

  best_count = 0
  best_dets: list[tuple[tuple[int, int, int, int], str]] = []
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


def count_qr_codes_worker(pdf_path: str, page_index: int, dpi: int) -> dict:
  """
  Worker function executed in a separate process.

  Responsibilities:
    - Render page -> image.
    - Decode QR codes with variant strategy.
    - Return:
        * count of QRs (deduplicated, best variant)
        * decoded payload of each QR (same order as the bounding boxes)
        * whether to rotate the page by 180° (QRs in header)
    - Catch all exceptions so main process can classify the page as buggy.

  Why process isolation:
    - ZBar is native code and can abort the process on assertion failures.
    - When that happens inside a worker process, only that worker dies; the main
      process continues and marks the page as buggy.
  """
  try:
    # Import inside worker so ZBar/native state lives in subprocess.
    import pyzbar  # noqa: F401

    img = render_page_to_pil(pdf_path, page_index, dpi)
    res = decode_qr_with_variants(img)

    count = int(res["count"])
    boxes = res["boxes"]
    values = list(res["values"])
    img_h = int(res["img_h"])

    # Orientation rule: ensure QR codes are in footer.
    rotate180 = False
    if count > 0 and _qr_in_header(boxes, img_h):
      rotate180 = True

    return {"ok": True, "count": count, "values": values, "rotate180": rotate180, "error": None}
  except Exception:
    # Any failure -> main process treats page as buggy.
    return {
      "ok": False,
      "count": 0,
      "values": [],
      "rotate180": False,
      "error": traceback.format_exc()
    }


def _apply_rotation_if_needed(page_obj: fitz.Page, rotate180: bool) -> None:
  """
  Apply output rotation in the resulting PDFs.

  Note:
    - This modifies the page rotation metadata (0/90/180/270).
    - It does not re-render and re-embed pixels; it's lightweight.
  """
  if not rotate180:
    return
  new_rot = (page_obj.rotation + 180) % 360
  page_obj.set_rotation(new_rot)


def write_split_pdfs(
  pdf_path: str,
  conforming_pages: list[int],
  buggy_pages: list[int],
  rotate_pages: set[int],
  conform_path: str,
  buggy_path: str
) -> tuple[str | None, str | None]:
  """
  Write the two output PDFs.

  Mechanism:
    - Open source PDF once.
    - Create two empty output PDFs.
    - Insert selected pages using insert_pdf (fast page copying).
    - Immediately after inserting each page, apply rotation if needed.

  Important:
    - PyMuPDF cannot save a PDF with zero pages.
    - Therefore, if one bucket is empty, that output file is skipped and None
      is returned for its path.
  """
  src = fitz.open(pdf_path)
  try:
    conform = fitz.open()
    buggy = fitz.open()

    try:
      for i in conforming_pages:
        conform.insert_pdf(src, from_page=i, to_page=i)
        out_page = conform.load_page(conform.page_count - 1)
        _apply_rotation_if_needed(out_page, i in rotate_pages)

      for i in buggy_pages:
        buggy.insert_pdf(src, from_page=i, to_page=i)
        out_page = buggy.load_page(buggy.page_count - 1)
        _apply_rotation_if_needed(out_page, i in rotate_pages)

      os.makedirs(os.path.dirname(os.path.abspath(conform_path)) or ".", exist_ok=True)
      os.makedirs(os.path.dirname(os.path.abspath(buggy_path)) or ".", exist_ok=True)

      saved_conform_path: str | None = None
      saved_buggy_path: str | None = None

      if conform.page_count > 0:
        conform.save(conform_path)
        saved_conform_path = conform_path

      if buggy.page_count > 0:
        buggy.save(buggy_path)
        saved_buggy_path = buggy_path

      return saved_conform_path, saved_buggy_path
    finally:
      conform.close()
      buggy.close()
  finally:
    src.close()


def write_report(
  report_path: str,
  input_pdf: str,
  conform_path: str | None,
  buggy_path: str | None,
  dpi: int,
  workers: int,
  page_count: int,
  violating_1based: list[int],
  rotate_pages: set[int],
  conforming_pages: list[int],
  buggy_pages: list[int]
) -> None:
  """
  Write a final summary report for auditability / downstream automation.
  This is separate from the continuous console output.

  Contents:
    - Input/output paths and runtime parameters
    - Counts of conformant/buggy pages
    - List of violating page numbers (1-based)
    - List of rotated page numbers (1-based)
  """
  os.makedirs(os.path.dirname(os.path.abspath(report_path)) or ".", exist_ok=True)

  rotate_1based = sorted([i + 1 for i in rotate_pages])

  with open(report_path, "w", encoding="utf-8") as f:
    f.write("QR Split Report\n")
    f.write("==============\n\n")
    f.write(f"Input:             {input_pdf}\n")
    f.write(f"Conformant output: {conform_path if conform_path else '[not written - no conformant pages]'}\n")
    f.write(f"Buggy output:      {buggy_path if buggy_path else '[not written - no buggy pages]'}\n")
    f.write(f"Pages:             {page_count}\n")
    f.write(f"DPI:               {dpi}\n")
    f.write(f"Workers:           {workers}\n\n")

    f.write(f"Conformant pages (exactly 2 QR): {len(conforming_pages)}\n")
    f.write(f"Buggy pages:                    {len(buggy_pages)}\n")

    f.write(f"\nViolating pages (1-based): {len(violating_1based)}\n")
    if violating_1based:
      f.write(", ".join(map(str, violating_1based)) + "\n")
    else:
      f.write("None\n")

    f.write(f"\nPages rotated 180° (QRs detected in header): {len(rotate_1based)}\n")
    if rotate_1based:
      f.write(", ".join(map(str, rotate_1based)) + "\n")
    else:
      f.write("None\n")


def _format_qr_values(values: list[str]) -> str:
  """
  Render decoded QR payloads for the console line.

  Notes:
    - Values are in bounding-box order (top-to-bottom, then left-to-right) as
      seen on the *unrotated* rendering, so a page flagged for 180° rotation
      lists them in the pre-rotation order.
    - Each payload is quoted so empty or space-containing values stay visible.
  """
  return ", ".join(f'"{v}"' for v in values)


class _TeeStream:
  """
  Text stream wrapper that mirrors every write into a second sink.

  Purpose:
    - The console output is the real audit trail of a run (per-page verdicts,
      QR payloads, crashes). Mirroring it lets us persist it into the report
      file without changing any of the existing print() calls.

  Behavior:
    - Writes go to the original stream first, so console behavior is unchanged
      even if the mirror sink misbehaves.
    - Unknown attributes are delegated to the wrapped stream, so code that
      inspects sys.stdout.encoding / .fileno() keeps working.
  """

  def __init__(self, stream, sink):
    self._stream = stream
    self._sink = sink

  def write(self, data) -> int:
    n = self._stream.write(data)
    try:
      self._sink.write(data)
    except ValueError:
      # Sink already closed (interpreter shutdown): console output still works.
      pass
    return n

  def flush(self) -> None:
    self._stream.flush()
    try:
      self._sink.flush()
    except ValueError:
      pass

  def __getattr__(self, name):
    return getattr(self._stream, name)


def _start_details_capture(report_path: str) -> None:
  """
  Capture everything printed to stdout/stderr and append it to the report file.

  Mechanism:
    - stdout/stderr are teed into an in-memory buffer for the whole run.
    - At interpreter exit the buffer is appended to the report file, i.e. after
      write_report() has written the summary section on top.

  Why atexit:
    - It also covers abnormal endings. If the run dies with an unhandled
      exception, the traceback goes through the tee first and therefore still
      lands in the file.

  Limitation:
    - This is a Python-level tee. Output a worker process writes straight to
      its own file descriptors - notably a native ZBar abort message - reaches
      the terminal but not the buffer. The main process reports such a page as
      "WORKER CRASH", and that line is captured.
  """
  buffer = io.StringIO()

  saved_stdout, saved_stderr = sys.stdout, sys.stderr
  sys.stdout = _TeeStream(saved_stdout, buffer)
  sys.stderr = _TeeStream(saved_stderr, buffer)

  def _append_details() -> None:
    # Restore first: nothing written from here on should be captured.
    sys.stdout, sys.stderr = saved_stdout, saved_stderr

    text = buffer.getvalue()
    buffer.close()
    if not text:
      return

    try:
      os.makedirs(os.path.dirname(os.path.abspath(report_path)) or ".", exist_ok=True)
      # Append: write_report() has already truncated and written the summary.
      with open(report_path, "a", encoding="utf-8") as f:
        f.write("\n\nDetailed Run Log\n")
        f.write("================\n\n")
        f.write(text)
        if not text.endswith("\n"):
          f.write("\n")
    except OSError as e:
      # Never let logging failures mask the run's own outcome.
      print(f"WARNING: could not append run log to {report_path}: {e}", file=sys.stderr)

  atexit.register(_append_details)


def main() -> int:
  p = argparse.ArgumentParser()
  p.add_argument("pdf", help="Input PDF path")
  p.add_argument("--dpi", type=int, default=250, help="Render DPI for decoding (default: 250)")
  p.add_argument(
    "--workers",
    type=int,
    default=max(1, (os.cpu_count() or 2) - 1),
    help="Number of worker processes (default: CPU-1)"
  )
  p.add_argument(
    "--conformant-out",
    dest="conformant_out",
    default=None,
    help="Path for conformant PDF output (default: <input_dir>/conformant.pdf)"
  )
  p.add_argument(
    "--buggy-out",
    dest="buggy_out",
    default=None,
    help="Path for buggy PDF output (default: <input_dir>/buggy.pdf)"
  )
  p.add_argument(
    "--report-out",
    dest="report_out",
    default=None,
    help=(
      "Path for final report text file, summary plus full run log "
      "(default: <input_dir>/qr_split_report.txt)"
    )
  )

  args = p.parse_args()

  # Normalize the input path so logging and output defaults are consistent.
  pdf_path = os.path.abspath(os.path.expanduser(args.pdf))
  if not os.path.exists(pdf_path):
    print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
    return 2

  out_dir = os.path.dirname(pdf_path)

  # Default outputs live next to the input unless overridden.
  conform_path = (
    os.path.abspath(os.path.expanduser(args.conformant_out))
    if args.conformant_out else os.path.join(out_dir, "conformant.pdf")
  )
  buggy_path = (
    os.path.abspath(os.path.expanduser(args.buggy_out))
    if args.buggy_out else os.path.join(out_dir, "buggy.pdf")
  )
  report_path = (
    os.path.abspath(os.path.expanduser(args.report_out))
    if args.report_out else os.path.join(out_dir, "qr_split_report.txt")
  )

  # Prevent accidental overwrite of the input PDF.
  try:
    if os.path.samefile(pdf_path, conform_path) or os.path.samefile(pdf_path, buggy_path):
      print("ERROR: Output path must be different from input PDF path.", file=sys.stderr)
      return 2
  except FileNotFoundError:
    # samefile can raise if outputs do not exist yet; ignore that case.
    pass

  # From here on, everything printed is also appended to the report file.
  _start_details_capture(report_path)

  # Read page count once in the main process for scheduling tasks.
  doc = fitz.open(pdf_path)
  try:
    page_count = doc.page_count
  finally:
    doc.close()

  conforming: list[int] = []
  buggy: list[int] = []
  rotate_pages: set[int] = set()
  violating_1based: list[int] = []

  processed = 0

  print(f"Input:             {pdf_path}", flush=True)
  print(f"Conformant output: {conform_path}", flush=True)
  print(f"Buggy output:      {buggy_path}", flush=True)
  print(f"Report output:     {report_path}", flush=True)
  print(f"Pages: {page_count} | DPI: {args.dpi} | Workers: {args.workers}\n", flush=True)

  # Submit one task per page. Each task runs in its own worker process.
  with ProcessPoolExecutor(max_workers=args.workers) as ex:
    futures = {ex.submit(count_qr_codes_worker, pdf_path, i, args.dpi): i for i in range(page_count)}

    # Iterate as pages finish (not necessarily in page order).
    for fut in as_completed(futures):
      i = futures[fut]
      processed += 1

      # If ZBar aborts a worker process, fut.result() may raise here.
      try:
        res = fut.result()
      except Exception as e:
        # Worker crash => treat page as buggy and record it as violating.
        buggy.append(i)
        violating_1based.append(i + 1)
        print(
          f"[{processed}/{page_count}] page {i + 1}: WORKER CRASH ({type(e).__name__}) -> BUGGY "
          f"| violating so far: {len(violating_1based)}",
          flush=True
        )
        continue

      if not res["ok"]:
        # Worker returned an explicit error (render/decoder issue) => buggy.
        buggy.append(i)
        violating_1based.append(i + 1)
        print(
          f"[{processed}/{page_count}] page {i + 1}: DECODER ERROR -> BUGGY "
          f"| violating so far: {len(violating_1based)}",
          flush=True
        )
        continue

      qr_count = int(res["count"])
      qr_values = list(res.get("values") or [])
      rotate180 = bool(res["rotate180"])

      # Store the rotation decision for later when we build the output PDFs.
      if rotate180:
        rotate_pages.add(i)

      rot_note = " | rotate 180" if rotate180 else ""

      # Primary classification rule:
      #   - exactly 2 QR codes => conformant
      #   - anything else => buggy / violating
      if qr_count == 2:
        conforming.append(i)
        print(
          f"[{processed}/{page_count}] page {i + 1}: OK (2 QR){rot_note} "
          f"| QR: {_format_qr_values(qr_values)} "
          f"| violating so far: {len(violating_1based)}",
          flush=True
        )
      else:
        buggy.append(i)
        violating_1based.append(i + 1)
        print(
          f"[{processed}/{page_count}] page {i + 1}: BUGGY ({qr_count} QR){rot_note} "
          f"| violating so far: {len(violating_1based)}",
          flush=True
        )

  # Sort for stable reporting and stable output PDF order.
  conforming.sort()
  buggy.sort()
  violating_1based.sort()

  print("\n=== Summary ===", flush=True)
  print(f"Violating pages: {len(violating_1based)}", flush=True)
  if violating_1based:
    print("Violating page numbers (1-based):", flush=True)
    print(", ".join(map(str, violating_1based)), flush=True)

  if rotate_pages:
    rotate_1based = sorted([i + 1 for i in rotate_pages])
    print(f"\nPages rotated by 180 degrees (QRs detected in header): {len(rotate_1based)}", flush=True)
    print(", ".join(map(str, rotate_1based)), flush=True)

  # Build and write both PDFs by copying selected pages from the source.
  saved_conform_path, saved_buggy_path = write_split_pdfs(
    pdf_path,
    conforming,
    buggy,
    rotate_pages,
    conform_path=conform_path,
    buggy_path=buggy_path
  )

  if saved_conform_path:
    print(f"\nWrote {saved_conform_path}", flush=True)
  else:
    print("\nSkipped conformant output: no conformant pages", flush=True)

  if saved_buggy_path:
    print(f"Wrote {saved_buggy_path}", flush=True)
  else:
    print("Skipped buggy output: no buggy pages", flush=True)

  # Write final report file for recordkeeping.
  write_report(
    report_path=report_path,
    input_pdf=pdf_path,
    conform_path=saved_conform_path,
    buggy_path=saved_buggy_path,
    dpi=args.dpi,
    workers=args.workers,
    page_count=page_count,
    violating_1based=violating_1based,
    rotate_pages=rotate_pages,
    conforming_pages=conforming,
    buggy_pages=buggy
  )
  print(f"Wrote {report_path}", flush=True)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())