#!/usr/bin/env bash

set -euo pipefail

# Determine top directory
script_source="${BASH_SOURCE[0]}"
# If invoked without a slash, it may come from PATH
if [[ "$script_source" != */* ]]; then
  script_source="$(command -v -- "$script_source" || true)"
fi

TOP_DIR="$(cd -P -- "$(dirname -- "$script_source")/.." && pwd -P)"

echo ""
echo "Top directory is: $TOP_DIR"
echo ""

if [[ $# -lt 7 ]]; then
  echo "Usage:   ./multiple.sh <examid> <grader-name> <questions-grading> <tag> <showbuttons?> <entermatrikel?> <showsummation?>"
  echo 'Example: ./multiple.sh "rnds-feb-2026" "Cap" "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17" "raw" true true true'
  exit 1
fi

EXAMID="$1"
GRADER="$2"
GRADING="$3"
TAG="$4"
SHOWBUTTONS="$5"
ENTERMATRIKEL="$6"
SHOWSUMMATION="$7"


# Anchored at TOP_DIR, not at the current working directory: the script must
# create its directories in the exam tree no matter where it is called from.
MY_DIR="$TOP_DIR/klausuren/$EXAMID/"

mkdir -p "$MY_DIR/build-corrections/"
mkdir -p "$MY_DIR/corrections/$GRADER/input-$TAG"
mkdir -p "$MY_DIR/corrections/$GRADER/completed-$TAG"
mkdir -p "$MY_DIR/pdf-exams-clean/"

# directory where we have all the cleaned, perfect pdfs which will now
# all be converted into a grading pdf 
DIR="$TOP_DIR/klausuren/$EXAMID/pdf-exams-clean/"

# Validate directory
if [[ ! -d "$DIR" ]]; then
  echo "Error: '$DIR' is not a directory"
  exit 1
fi

shopt -s nullglob  # avoid literal "*.pdf" if none exist

echo "NOW iterating on $DIR/*.pdf"
echo ""

shopt -s nullglob

for file in "$DIR"/*.pdf; do
  base="${file##*/}"          # filename only (no path)
  name="${base%.pdf}"         # remove .pdf extension
#  SERIAL="${name:0:4}"        # first 4 characters (bash substring)
  SERIAL="${name}"
  echo -e "\n\n"
  echo "********** Command is: ${TOP_DIR}/driver/single.sh \"$EXAMID\" \"$GRADER\" \"$GRADING\" \"$SERIAL\"  \"$TAG\" $SHOWBUTTONS $ENTERMATRIKEL $SHOWSUMMATION"
  ${TOP_DIR}/driver/single.sh "$EXAMID" "$GRADER" "$GRADING" "$SERIAL" "$TAG" $SHOWBUTTONS $ENTERMATRIKEL $SHOWSUMMATION
  echo "Command completed"
done


# Build the grading queue for the trusted-JS workflow: one line per correction
# PDF in the grader's directory. START.pdf is excluded, it is only the bootstrap
# document and not an exam to be graded.
# The queue is rebuilt from scratch on every run, so leftovers of a previous run
# cannot survive in it.
CORR_DIR="${TOP_DIR}/klausuren/${EXAMID}/corrections/${GRADER}"
QUEUE_FILE="${CORR_DIR}/queue.txt"





: > "$QUEUE_FILE"
queue_count=0

# nullglob is set above, so an empty directory yields an empty list, not "*.pdf".
# The glob is expanded in sorted order, which keeps the queue deterministic.
for pdf in "$CORR_DIR/input-$TAG"/*.pdf; do
  pdfname="${pdf##*/}"
  if [[ "$pdfname" == "START.pdf" ]]; then
    continue
  fi
  echo "input-$TAG/$pdfname" >> "$QUEUE_FILE"
  queue_count=$((queue_count + 1))
done

echo ""
echo "Wrote $QUEUE_FILE with $queue_count entry/entries"


# copy in the START.pdf bootstrap file for graders using this approach
cp "$TOP_DIR/sty/build/START.pdf" "${TOP_DIR}/klausuren/${EXAMID}/corrections/${GRADER}/"



echo "DONE"