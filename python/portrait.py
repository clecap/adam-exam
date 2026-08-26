#!/usr/bin/env python3
"""
Make all pages in a PDF portrait by rotating any landscape pages
90 degrees counter-clockwise.

By default writes output as 'portrait.pdf' into the same directory as the
input PDF and writes a report as 'portrait_rotation_report.txt'.

Usage:
  python3 portrait.py /path/to/input.pdf
  python3 portrait.py /path/to/input.pdf -o /path/to/output.pdf
  python3 portrait.py /path/to/input.pdf -o out.pdf -r report.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
  # pypdf is the actively maintained fork of PyPDF2
  from pypdf import PdfReader, PdfWriter
except ImportError as e:
  raise SystemExit(
    "Missing dependency: pypdf\n"
    "Install with: python3 -m pip install --upgrade pypdf"
  ) from e


def _get_rotation_degrees(page) -> int:
  rot = page.get("/Rotate", 0)
  try:
    rot = int(rot)
  except Exception:
    rot = 0
  return rot % 360


def _effective_dimensions(page) -> tuple[float, float]:
  """
  Returns (effective_width, effective_height) as they are displayed,
  taking the page's current /Rotate into account.
  """
  w = float(page.mediabox.width)
  h = float(page.mediabox.height)
  rot = _get_rotation_degrees(page)
  if rot in (90, 270):
    return h, w
  return w, h


def _rotate_ccw_90(page) -> None:
  """
  Rotate page counter-clockwise by 90 degrees in a way that works across
  pypdf/PyPDF2 variants.
  """
  if hasattr(page, "rotate_counter_clockwise"):
    page.rotate_counter_clockwise(90)
    return
  if hasattr(page, "rotateCounterClockwise"):
    page.rotateCounterClockwise(90)
    return
  # Fallback: pypdf's rotate(angle) is clockwise-positive, so CCW 90 == -90
  if hasattr(page, "rotate"):
    page.rotate(-90)
    return
  raise RuntimeError("This pypdf/PyPDF2 version does not support rotation APIs.")


def portraitify(input_pdf: Path, output_pdf: Path | None = None, report_txt: Path | None = None) -> tuple[Path, list[int], Path]:
  if not input_pdf.exists():
    raise FileNotFoundError(f"Input file not found: {input_pdf}")
  if input_pdf.suffix.lower() != ".pdf":
    raise ValueError(f"Input does not look like a PDF: {input_pdf}")

  if output_pdf is None:
    output_pdf = input_pdf.with_name("portrait.pdf")
  if report_txt is None:
    report_txt = input_pdf.with_name("portrait_rotation_report.txt")

  # Defensive: avoid overwriting the input by accident
  if output_pdf.resolve() == input_pdf.resolve():
    raise ValueError("Output PDF path must be different from input PDF path.")

  reader = PdfReader(str(input_pdf))
  writer = PdfWriter()

  rotated_pages: list[int] = []

  total = len(reader.pages)
  print(f"Input:  {input_pdf}", flush=True)
  print(f"Output: {output_pdf}", flush=True)
  print(f"Report: {report_txt}", flush=True)
  print(f"Pages:  {total}", flush=True)
  print("-", flush=True)

  for i, page in enumerate(reader.pages, start=1):
    ew, eh = _effective_dimensions(page)
    is_landscape = ew > eh

    if is_landscape:
      _rotate_ccw_90(page)
      rotated_pages.append(i)
      print(f"[{i:>4}/{total}] landscape -> rotated CCW 90°", flush=True)
#    else:
#      print(f"[{i:>4}/{total}] portrait  -> ok", flush=True)

    writer.add_page(page)

  output_pdf.parent.mkdir(parents=True, exist_ok=True)
  with output_pdf.open("wb") as f:
    writer.write(f)

  report_txt.parent.mkdir(parents=True, exist_ok=True)
  with report_txt.open("w", encoding="utf-8") as f:
    f.write(f"Input:  {input_pdf}\n")
    f.write(f"Output: {output_pdf}\n")
    f.write(f"Total pages: {total}\n")
    f.write(f"Rotated pages (1-based): {rotated_pages if rotated_pages else 'None'}\n")

  print("-", flush=True)
  if rotated_pages:
    print(f"Rotated pages (1-based): {rotated_pages}", flush=True)
  else:
    print("No pages needed rotation.", flush=True)
  print(f"Wrote: {output_pdf}", flush=True)
  print(f"Wrote: {report_txt}", flush=True)

  return output_pdf, rotated_pages, report_txt


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Rotate landscape pages to portrait (CCW 90°) and write an output PDF."
  )
  parser.add_argument("input_pdf", type=str, help="Path to input PDF")
  parser.add_argument(
    "-o",
    "--output",
    dest="output_pdf",
    type=str,
    default=None,
    help="Path to output PDF (default: portrait.pdf next to input)"
  )
  parser.add_argument(
    "-r",
    "--report",
    dest="report_txt",
    type=str,
    default=None,
    help="Path to report text file (default: portrait_rotation_report.txt next to input)"
  )

  args = parser.parse_args()

  input_pdf = Path(args.input_pdf).expanduser().resolve()
  output_pdf = Path(args.output_pdf).expanduser().resolve() if args.output_pdf else None
  report_txt = Path(args.report_txt).expanduser().resolve() if args.report_txt else None

  portraitify(input_pdf, output_pdf=output_pdf, report_txt=report_txt)


if __name__ == "__main__":
  main()