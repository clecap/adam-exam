






Observation 1: There are some pages which do not have QR codes but just are plainly white pages,
artefacts of the scanner process or foreign pages possibly containing some random scribble but no QR codes.

Observation 2: Interestingly enough, but there are some pages which the scanner scans in landscape position
and not in portrait position.

Prompt:
I have a large PDF file where all pages should be in portrait. 
However, possibly due to scanner glitch, some pages are in landscape. 
Provide python code which outputs the PDF file where all pages
are in portrait. For transforming landscape into portrait, use counter
clockwise rotation.
Provide a report on which pages had to be rotated.
Provide this as a continous printout while working on the PDF, not
just at the end after job completion, so that the user can watch the
progress of the algorithm.
Write the result to file portrait.pdf.
The result file should be written into the same directory
in which the input pdf file resides in.

Step 1:  ./portrait.py data/scan.pdf     
  generates data/portrait.pdf







Prompt:
I have a large PDF file. Every page should contain exactly two QR code blocks.
Some pages might violate this requirements. I need python code which
1) prints out the number of the pages violating this requirement.
2) generates a file conformant.pdf which contains all conforming pages.
3) generates a file buggy.pdf which contains all non-conforming pages.
Minimize Zbar decoder errors such as
  _zbar_decode_databar: Assertion "seg->finder >= 0" failed.
by restricting the decoder by constructions such as
  decoded = decode(image, symbols=[ZBarSymbol.QRCODE])
The print-out should be done continuously while working on the PDF, not
just at the end after job completion, so that the user can watch the
progress of the algorithm.
The files conformant.pdf and buggy.pdf should be written into the same directory
in which the input pdf file resides in.

This produces clean.py


Additional prompt:
The program is fine thus far but it classifies one pages as defective although this page clearly has two QR codes. 
This happens with dpi 400. What can I do to improve?

This produces clean2.py


Result: conformant.pdf


Additional prompt:
This program is absolutely great. Now I need one further modification.
The pages should be in such a form that the QR codes are in the footer, not in the header.
Pages with a QR code in the header should be rotated by 180 degrees.
The rest of the program should stay as it is.
Provide a complete program again.

This produces clean3.py




I have a PDF with many pages. 
Every page contains two QR codes in the footer. 
The left QR code has the form P followed by a number, which denotes the QR-page-number. 
The right QR code has the form S followed by a number, which denotes the QR-serial-number.
For every QR-serial-number s I need to generate a PDF file whose name is s.pdf with leading
zeroes added, such that the first part of the file name always contains 4 decimal digits.
This file must contain all the pages with QR-serial-number s.
In every file, the pages should be ordered by QR-page-number in the sequence 1, 2, 3 and so on.
If in this sequence a page number is missing, the missing page should be represented by a page with
the text "missing page with page number p" and p should be the missing page number.
Report about all situations.
The reporting should be done continuously while working on the PDF, not
just at the end after job completion, so that the user can watch the
progress of the algorithm.
The files should be written into the same directory
in which the input pdf file resides in.
Provide the complete Python program doing this.

This gives split.py


Additional Prompt:
I need some changes.
1) I am getting a considerable number of decoding errors for the QR code, especially for the right one.
Improve the QR detection.
2) I do not need reports when a source page is added, only when a missing page is generated.
3) When a page number is duplicate, I need an error message
Provide the complete program.

This gives split2.py

Additional Prompt:
This is already very good.
I need the following adaptations.
1) In case of a duplicate page number, only include the page once, but report on the fact of the duplicate.
2) The running time is very high. Maybe we can make the QR detection a bit more light-weight without sacrificing too much precision.
3) The running time is very high and the CPU load is low. Is it possible to parallelize the task on multiple processors to make it faster?
If yes, do so. Ensure proper data integrity when parallelizing the task.
4) I need to be able to enter an expected page number per file. Add placeholders and report when a file has less pages.
5) Mark extraordinary situations (duplicates, placeholders, failed QR detections) with ****** in the report.
Provide the complete program.


This gives split3.py




I have a directory of PDF files. For all files whose name consist of numbers only,
do the following task:
On the second page in the lower part of the page
there is a handwritten number consisting of nine numbers, which should be
written in 7-segment notation.
I need you to detect this number. If the number is not strictly written in 
7-segment notation, try to decode the number nevertheless.
Then rename the file by appending a dash and the detected number to the file name.
Report about all situations where you cannot properly decode this number.
In this case, append a dash and the text ERROR to the file name.
The reporting should be done continuously while working on the PDF, not
just at the end after job completion, so that the user can watch the
progress of the algorithm.
Provide a Python program for this task.

This yields matrikel.py, which is a complete failure.

Additional prompt:
Ok. Looks like the character recognition including the 7-segment detection completely fails in all files. I will upload a sample page 2. This is the entire page 2. The area to read is below the text Matrikelnummer hier eintragen. In the sample it is 2192005544
I need an improved program!

This yields matrikel2.py which also is a complete failure.


additional prompt:
This is just completely wrong. Not a single detection is correct. The green box is too high and includes the text "Matrikelnummer hier eintragen..." The green box should focus on the area below this text "Matrikelnummer hier eintragen..."



Prompt:
I have three PDF files with checkboxes and Textfields.
The contents of the PDF file is identical but the checkboxes and Textfields
are not.
I need another instance of the PDF file where the contents of the
checkboxes and Textfields is merged.
Produce a Python program for this.









duplicates ??? --- still lacking this !!!
missing pages ??? --- at the end ---- how is this treated - what is the reference number of pages we need.



 




  Further observations:
  * We cannot easily merge PDF files where every singel one has document level javascript, as this corrupts the adobe dictionary in pdf.
  * pdfTex and luatex fails to include some 100+ pdf files into a target pdf
  * 



  