# 


# Phases

In our process model, an exam consists of the following phases.


1. **Preparing** is the process where the exam text is prepared by the examiner.
This phase is done by the examiner and consists of typesetting a single
exam sheet according to sample XXXXX.

1. **Printing** is the process of producing a sufficient number of exam sheets for all participating students.
This is done by wrapping the entire exam into a LaTeX ```\begin{copies}{number} ... \end{copies}``` environment.

 As a result a single PDF is generated which contains the required number of exam sheets. It provides every exam sheet with a uniquely
identifying serial number, which also gets encoded in a QR code.

This process may run quite some time, especially if a larger number
of exam sheets must be set. 

Take care to run the LaTeX compilation the required number of times
until the references stabilized.


1. **Scanning** is the process of converting the exam sheets into a PDF file.



1. **Pre-Grading**



1. **Grading**
1. **Merging** 
1. **Auditing**



All phases are executed on a single (preferably) Linux / MacOS node where




# OLD NOTES

## Scan Preparaiont and Cleaning

1. Place all pdf scans of the exams into directory klausuren/<examid>/scan-input. 

* The file extension shoudl be .pdf
* The scan may consist of several parts and may contain several scan runs of the same pile of sheets.
* In case of scan problems, simply scan the offending pages or even all pages again and add the filese to this directory. Run the below script again. Duplicates are discarded automagically.

2. On Docker do

```./driver/driver.sh <examid>``` 

3. Directory ```pdf-exams-clean``` should now contain the exam sheets, ready for further processing

## Splitting 


Step 3: Split exam files into grading files.

Select graders and questions
Marvin  1,2,3,4
Cap   5,6,7
call ./multiple.sh   in a shell where latex is present

generates directory corrections and there CLEAN as well as every corrector

* upload that to iukp


## Without Driver

* Scan in all the pages into file scan.pdf

*  ./portrait.py data/scan.pdf     
  generates data/portrait.pdf
* ./clean3.py data/portrait.pdf
  generates data/conformant.pdf
* ./split3.py data/conformant.pdf
  generates individual serials
* Compile those to


DO THIS AND RENAME PROPERLY: 
gs -o 0004-fixed.pdf -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress -dCompatibilityLevel=1.7 0004.pdf

MUST sanitize with ghostscript - and need to make sure correct directory is used.


Turn directory of PDF files into suitable latex command part


## Debugging the Scan

Scanning the sheets can be affected by a number of errors.

There are two types of errors.

* Type 1: Errors in the provided material. These errors cannot be fixed. They can comprise:
  * Superfluos pages which were not part of the exam.
  * Missing pages which were not rendered by the students.
  * Pages which 


* Type 2: Errors in the scan process can comprise:
  * Pages which were rotated durign the scan process
  * Pages which were scanned only partially
  * Empty or defective pages which were added during the scan process
  * Pages which were not scanned at all during the scan process



## Overview on Python Scripts

* clean4.py




## Merging Corrections



merge-forms-2.py 

./merge-forms-2.py "$FILE-CLEAN.pdf" "$FILE-Cap.pdf" "$FILE-Davieds.pdf" "$FILE-Mundt.pdf" -o "$FILE-OUTPUT.pdf"


## Debugging, Auditing and Manual Processing

list-fields.py <FILEPATH>.pdf    lists all fields found in the PDF

list-fields-2.py <FILEPATH>.pdf  lists all fields found in the PDF and produces a <FILEPATH>.out and a <FILEPATH>.json with the fields information

list-fields-3.py <FILEPATH>.pdf  lists all fields found in the PDF and produces a <FILEPATH>.out and a <FILEPATH>.json with the fields information and
                                 a <FILEPATH>-maps.json which only maps field names to field values 





# Instructions for graders


Place the directory containing the PDF files into the list of trusted directories in preferences -> Security (enhanced)