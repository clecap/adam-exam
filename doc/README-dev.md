# Development Notes

## JS inside of PDF
* Is very fragile
+ Only is pre-ECMA15 JS without all the 'new' features.
* CAVE: After a \n in a JS file there must be a blank or the parser chokes
* CAVE: If there is a ) or } or otherwise unbalanced bracket inside of a comment (!) the parser chokes and ruins the PDF.
* The PDF interface for Javascript might be spec-conformant but often is not what a programmer might expect.
* setTimout does not exist, but app.setTimeOut (sic!) does and has a different signature, no functions but strings.
* The validation functions for a TextField behave very strangely.
* The are many other reasons why I cannot really recommend Adobe's approach to Javascript.

## PDF
* We cannot (easily) merge PDF files where every single one has document level javascript, as this corrupts the adobe dictionary in pdf.
  
  
## TeX  
* pdfTex and luatex fail to include some 100+ or more pdf files into a target pdf
  