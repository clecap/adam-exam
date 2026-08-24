# NEW NOTES


* clean4.py











# OLD NOTES

## With Driver:

```
* Place file   scan-<examid>.pdf into directory klausuren/<examid>/pdf-scans
* ./driver.sh <examid>
** Produces pdf-exams-raw
```

Copy into pdf-exams-clean the completely workign ones (still bug in workflow)


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

