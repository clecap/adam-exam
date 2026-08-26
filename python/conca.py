#!/usr/bin/env python3
"""
Concatenate all PDF files of a directory into one PDF file.

Usage:
  conca.py <source-dir> <output-pdf>

Both parameters are obligatory: the directory to read from, and the full path
of the PDF file to write. The output name is used exactly as given.

Behavior:
  - Collects the *.pdf files of the source directory itself. Subdirectories are
    not traversed.
  - Concatenates them in file system order, i.e. the order os.listdir() returns.
    That order is not sorted and not guaranteed to be stable across systems;
    the console output lists the files in the order actually used.
  - Writes the result to the given output path. Its directory is created if it
    does not exist.

Safety:
  - An existing output file is never overwritten. The run stops with an error.
  - The output file is skipped as an input, so writing the result into the
    source directory cannot fold a previous result into a new one.
  - A broken PDF - one that cannot be opened or that has no pages - terminates
    the run with an error message. A silently incomplete concatenation would be
    worse than no result.

Install (macOS):
  python3 -m pip install pymupdf
"""

import argparse
import os
import sys

import fitz  # PyMuPDF: fast PDF page copying


def find_pdfs(source_dir: str, exclude: str | None) -> list[str]:
  """
  Collect PDF files from the source directory.

  Notes:
    - Only regular files ending in .pdf (case-insensitive) are taken.
    - Subdirectories are ignored.
    - The order is the file system order of os.listdir(), unsorted.
    - `exclude` is the absolute path of the planned output file: it must never
      become one of its own inputs.
  """
  found: list[str] = []

  for name in os.listdir(source_dir):
    path = os.path.join(source_dir, name)
    if os.path.isfile(path) and name.lower().endswith(".pdf"):
      found.append(path)

  if exclude:
    found = [p for p in found if os.path.abspath(p) != exclude]

  return found


def concatenate(pdf_paths: list[str], out_path: str) -> tuple[int, int]:
  """
  Concatenate the given PDFs into out_path.

  Returns:
    (pages_written, files_merged)

  Mechanism:
    - insert_pdf copies pages without re-rendering, so quality is untouched.

  Error handling:
    - A file that cannot be opened, or that contains no pages, terminates the
      run. Nothing is written in that case, because the output file is saved
      only after every input has been merged successfully.
  """
  out = fitz.open()
  merged = 0

  try:
    for path in pdf_paths:
      try:
        src = fitz.open(path)
      except Exception as ex:
        raise RuntimeError(f"Cannot open {path}: {ex}") from ex

      try:
        if src.page_count == 0:
          raise RuntimeError(f"File contains no pages: {path}")

        out.insert_pdf(src)
        merged += 1

        print(f"  + {os.path.basename(path)}: {src.page_count} page(s)", flush=True)
      finally:
        src.close()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    out.save(out_path)
    return out.page_count, merged
  finally:
    out.close()


def main() -> int:
  p = argparse.ArgumentParser(
    description="Concatenate all PDFs of a directory into one PDF file."
  )
  p.add_argument("source_dir", help="Directory containing the PDF files to concatenate (obligatory)")
  p.add_argument("output_pdf", help="Full path of the PDF file to write (obligatory)")

  args = p.parse_args()

  source_dir = os.path.abspath(os.path.expanduser(args.source_dir))
  out_path = os.path.abspath(os.path.expanduser(args.output_pdf))

  if not os.path.isdir(source_dir):
    print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
    return 2

  # A directory as output path would make the save fail with a confusing error.
  if os.path.isdir(out_path):
    print(f"ERROR: Output path is a directory, expected a file name: {out_path}", file=sys.stderr)
    return 2

  # Never overwrite: an existing result is always an error.
  if os.path.exists(out_path):
    print(f"ERROR: Output already exists, refusing to overwrite: {out_path}", file=sys.stderr)
    return 2

  pdfs = find_pdfs(source_dir, exclude=out_path)
  if not pdfs:
    print(f"ERROR: No PDF files found in {source_dir}", file=sys.stderr)
    return 2

  print(f"Source: {source_dir}", flush=True)
  print(f"Output: {out_path}", flush=True)
  print(f"Files:  {len(pdfs)}\n", flush=True)

  try:
    pages, merged = concatenate(pdfs, out_path)
  except Exception as ex:
    print(f"ERROR: {ex}", file=sys.stderr)
    return 1

  print(f"\nWrote {out_path}", flush=True)
  print(f"Merged {merged} file(s), {pages} page(s) total", flush=True)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
