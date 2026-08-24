#!/usr/bin/env bash

set -euo pipefail

# Determine top directory
script_source="${BASH_SOURCE[0]}"
# If invoked without a slash, it may come from PATH
if [[ "$script_source" != */* ]]; then
  script_source="$(command -v -- "$script_source" || true)"
fi

TOP_DIR="$(cd -P -- "$(dirname -- "$script_source")/.." && pwd -P)"

if [ "$#" -ne 7 ]; then
  echo "Usage:   ./single.sh <examid> <grader-name> <questions-grading> <serialnumber> <showbuttons?> <entermatrikel?> <showsummation?>"
  echo 'Example: ./single.sh "rnds-feb-2026" "ClemensCap" "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17" "0004" true true false'
  exit 1
fi

EXAMID="$1"
GRADER="$2"
GRADING="$3"
SERIAL="$4"
SHOWBUTTONS="$5"
ENTERMATRIKEL="$6"
SHOWSUMMATION="$7"


ADAM_VERSION="v1.1"
ADAM_PATH="../sty/"

#### export TEXINPUTS="${TOP_DIR}/sty"

ADAM="${ADAM_PATH}adam-exam-${ADAM_VERSION}"

printf "TOP_DIR is ${TOP_DIR} \n"
printf "ADAM is ${ADAM} \n"
printf "TEXINPUTS is ${TEXINPUTS} \n"

kpsewhich ${ADAM}

printf "DONE KPSE"

# SOURCE="\documentclass{./adam-exam-v1}\examSerial{0004}\grading{1,2,3,4}{Cap}\examId{rnds-feb-2026}\makecorrection"

SOURCE="
  \documentclass{${ADAM}}
  \grading{${GRADING}}{${GRADER}}
  \examId{$EXAMID}

  \setbool{showbuttons}{$SHOWBUTTONS}
  \setbool{entermatrikel}{$ENTERMATRIKEL}
  \setbool{showsummation}{$SHOWSUMMATION}

  \preparecorrection

  \begin{document}
  \makecorrection{$SERIAL}
  \end{document}
"

BUILD_DIRECTORY="klausuren/$EXAMID/build-corrections/"
JOBNAME="${SERIAL}-${EXAMID}-${GRADER}"

printf "    hhhhh TEXINPUTS is: ${TEXINPUTS} \n"

printf "NOW"

# compile to pdf
pdflatex -jobname="$JOBNAME" -recorder -output-directory="$TOP_DIR/klausuren/$EXAMID/build-corrections" ${SOURCE}
# run twice in order to get the references correct
pdflatex -jobname="$JOBNAME" -recorder -output-directory="$TOP_DIR/klausuren/$EXAMID/build-corrections" ${SOURCE}

# move to directory for proper grader 
mv "$TOP_DIR/klausuren/$EXAMID/build-corrections/$JOBNAME.pdf" "$TOP_DIR/klausuren/$EXAMID/corrections/$GRADER/"

printf "Completed \n"