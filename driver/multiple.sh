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

if [[ $# -lt 6 ]]; then
  echo "Usage:   ./multiple.sh <examid> <grader-name> <questions-grading> <showbuttons?> <entermatrikel?> <showsummation?>"
  echo 'Example: ./multiple.sh "rnds-feb-2026" "Cap" "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17" true true true'
  exit 1
fi

EXAMID="$1"
GRADER="$2"
GRADING="$3"
SHOWBUTTONS="$4"
ENTERMATRIKEL="$5"
SHOWSUMMATION="$6"


MY_DIR="klausuren/$EXAMID/"

mkdir -p "$MY_DIR/build-corrections/"
mkdir -p "$MY_DIR/corrections/$GRADER/"
mkdir -p "$MY_DIR/corrections/"
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
  echo "********** Command is: ${TOP_DIR}/driver/single.sh \"$EXAMID\" \"$GRADER\" \"$GRADING\" \"$SERIAL\" $SHOWBUTTONS $ENTERMATRIKEL $SHOWSUMMATION"
  ${TOP_DIR}/driver/single.sh "$EXAMID" "$GRADER" "$GRADING" "$SERIAL" $SHOWBUTTONS $ENTERMATRIKEL $SHOWSUMMATION
  echo "Command completed"

  exit 1

done



echo "DONE"