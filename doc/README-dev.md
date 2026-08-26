# Development Notes

## JS inside of PDF
* Is very fragile
+ Only is pre-ECMA15 JS without all the 'new' features.
* After a \n in a JS file there must be a blank or the parser chokes


## PDF
* We cannot (easily) merge PDF files where every single one has document level javascript, as this corrupts the adobe dictionary in pdf.
  
  
## TeX  
* pdfTex and luatex fail to include some 100+ or more pdf files into a target pdf
  