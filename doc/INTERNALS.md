This document describes some internal structures used in adam-exam.

# Directories

## System Directory

| Directory  | Meaning                                 |
| ---------- | --------------------------------------- |
| .vscode/   | Visual Studio Code settings             |
| customize/ | Document parts which can be customized  |
| dev/       | Some tests during development           |
| docker/    | Docker environment                      |
| doc/       | Documentation                           |
| js/        | Javascript Files                        |
| python/    | Python scripts                          |
| sty/       | TeX style and class files for inclusion |
| klausuren/ | Contains sample exams                   |

## Exam Directory

klausuren/&lt;EXAM-ID&gt;
klausuren/rnds-feb-2026 top-directory of the specific exam

| Subdirectory | Meaning                                              |
| ------------ | ---------------------------------------------------- |
| tex/         | tex data of the exam                                 |
| tex/build/   | build area for the exam                              |
| pdf-scans/   | scans of the exam sheets                             |
| pdf-exams-raw/ |   |
| pdf-exams-clean/   | scanned and properly processed individual exam files |
| corrections/ | contains the directories for every grader                     |


# Files

# TeX generated Files

TeX moves around information in files. These are the employed files.

| Filename    | Meaning                                                                                                                     |
| ----------- | --------------------------------------------------------------------------------------------------------------------------- |
| jobname.tot | Contains the total number of points which may be achieved in the entire exam                                                |
| jobname.sol | Contains the information for typesetting the correct answers and thhe grading user interface for every question of the exam |
| jobname.crd | Contains the positions where the form elements for the total number of points per question should be typeset                |


# Form Codes:

```
<num>C        optional comment to question <num>

<question>  Number of the question
<serial>    exam serial
<chkbox>    separate counter of chekboxes per question and serial

<question>-<serial>      Pushbutton for all 
D<question>-<serial>      Points for discretionary grading

Z<question>-<serial>                   checkbox for completion
grp<question>-<serial>                 adjustment radio group
<question>X <chkbox>-<serial>          Point box
H<question>-<hintboxnumber>-<serial>   Hint box

punkte<question>-<serial>   points on question

grader\currentQuestion-\myexamserial    Name of the grader

punktesumme-<serial>
matrikel-<serial>
prozent-<serial>
note-<serial>

PushButton
Textfield
ChoiceMenu
```

