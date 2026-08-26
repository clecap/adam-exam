#!/usr/bin/env bash

# exit on error, unset variables are an error, pipe of commands fail if any command in the pipe fails
set -euo pipefail


if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <examid>"
  exit 1
fi

EXAMID="$1"

# TOP_DIR is the directory in which which all exam files shall be stored
TOP_DIR="/app/klausuren/"


WORKFLOW_INPUT="$TOP_DIR/$EXAMID/scan-input/"



RAW_SCAN_FILE="$TOP_DIR/$EXAMID/pdf-scans/scan-${EXAMID}.pdf"
PORTRAIT_SCAN_FILE="$TOP_DIR/$EXAMID/pdf-scans/portrait-${EXAMID}.pdf"
PORTRAIT_SCAN_REPORT="$TOP_DIR/$EXAMID/pdf-scans/portrait-report-${EXAMID}.txt"
CONFORMANT_SCAN_FILE="$TOP_DIR/$EXAMID/pdf-scans/conformant-scan-${EXAMID}.pdf"
BUGGY_SCAN_FILE="$TOP_DIR/$EXAMID/pdf-scans/buggy-scan-${EXAMID}.pdf"
CLEANING_REPORT="$TOP_DIR/$EXAMID/pdf-scans/cleaning-report-${EXAMID}.txt"
OPTIMIZED_SCAN_FILE="$TOP_DIR/$EXAMID/pdf-scans/optimized-$EXAMID.pdf"

PYTHON_PATH="/app/python/"

# files required for the latex runs
TOT_FILE="${EXAMID}.tot"
SOL_FILE="${EXAMID}.sol"
CDR_FILE="${EXAMID}.cdr"

#if [ ! -f "$TOT_FILE" ]; then
#  echo "Error: File '$TOT_FILE' does not exist or is not a regular file." >&2
#  exit 1
#fi

#if [ ! -f "$SOL_FILE" ]; then
#  echo "Error: File '$SOL_FILE' does not exist or is not a regular file." >&2
#  exit 1
#fi

#if [ ! -f "$CDR_FILE" ]; then
#  echo "Error: File '$CDR_FILE' does not exist or is not a regular file." >&2
#  exit 1
#fi


rm -f $RAW_SCAN_FILE


echo "Concatenating all pdf files in directory $WORKFLOW_INPUT"
  ${PYTHON_PATH}/conca.py ${WORKFLOW_INPUT} ${RAW_SCAN_FILE}
echo "DONE concatenating"


if [ ! -f "$RAW_SCAN_FILE" ]; then
  echo "Error: File '$RAW_SCAN_FILE' does not exist or is not a regular file." >&2
  exit 1
fi


echo "Rotating all scanned pages of ${RAW_SCAN_FILE} to portrait and generating ${PORTRAIT_SCAN_REPORT}"
  ${PYTHON_PATH}/portrait.py "$RAW_SCAN_FILE" -o "$PORTRAIT_SCAN_FILE" -r "$PORTRAIT_SCAN_REPORT"
echo "DONE"

echo "Cleaning up: Calling clean5.py"
  ${PYTHON_PATH}/clean5.py --conformant-out  "$CONFORMANT_SCAN_FILE"  --buggy-out "$BUGGY_SCAN_FILE" --report-out "$CLEANING_REPORT" "$PORTRAIT_SCAN_FILE"
echo "Cleaned up"

echo -e "\nImproving the PDF quality of the resulting PDF"
  qpdf --object-streams=disable "$CONFORMANT_SCAN_FILE" "$OPTIMIZED_SCAN_FILE"
echo "IMPROVED"

echo -e "\nSplitting the result in place: Running split5.py"
  mkdir -p $TOP_DIR/$EXAMID/pdf-exams-raw
  cp $OPTIMIZED_SCAN_FILE $TOP_DIR/$EXAMID/pdf-exams-raw
  ${PYTHON_PATH}/split5.py "$TOP_DIR/$EXAMID/pdf-exams-raw/optimized-$EXAMID.pdf"
echo "SPLITTED"
echo ""

echo "Cleaning up individual fles"
mkdir -p ${TOP_DIR}/${EXAMID}/pdf-exams-clean/

# Collect first, so the progress output can show "n of total".
# nullglob: an unmatched pattern yields an empty list instead of the pattern itself.
shopt -s nullglob
pdffiles=("$TOP_DIR/$EXAMID/pdf-exams-raw"/[0-9][0-9][0-9][0-9].pdf)
shopt -u nullglob

total=${#pdffiles[@]}
count=0
for pdf in "${pdffiles[@]}"; do
  [ -e "$pdf" ] || continue
  count=$((count + 1))
  pdffilename="${pdf##*/}"
  echo "[$count/$total] Cleaning $pdf into $TOP_DIR/$EXAMID/pdf-exams-clean/$pdffilename"
  qpdf --object-streams=disable "$pdf" "$TOP_DIR/$EXAMID/pdf-exams-clean/$pdffilename"
done
echo "Cleaned up $count file(s)"


#for pdf in "$TARGET_DIR"/[0-9][0-9][0-9][0-9].pdf; do
#  [ -e "$pdf" ] || continue
#  tmp="${pdf}.gs-tmp"
#  echo "gs on $pdf"
#  gs -sDEVICE=pdfwrite \
#    -dCompatibilityLevel=1.7 \
#    -dPDFSETTINGS=/prepress \
#    -dNOPAUSE -dBATCH \
#    -sOutputFile="$tmp" \
#    "$pdf"
#  mv "$tmp" "$pdf"
#done
#echo "gsed up" 
