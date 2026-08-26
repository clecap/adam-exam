# Description

Adam-Exam is a solution for automating 
* the generation of printable PDF-based exam sheets and grading schemes
* the scanning, checking, and archiving of exam sheets
* the grading process, especially when distributed among several graders
* the documentation of the grading and evaluating schemes

It supports the following exam life cycle:

1 The instructors design an exam sheet and a specification of the evaluation schemes, using the provided LaTeX macros. The output of this phase is a PDF file with all the exam sheets,
suitably encoded by page and serial numbers in QR codes and ready to be printed.
2 The team assistants print the PDF file, distribute the exam sheets to the students, collect the sheets again and scan them. 
3 The provided scripts sort, rotate and select the 


# Installation

## Requirements

1 A working LaTeX compilation environment (I am using Texlive)
2 A working docker installation (I am using Dockerhub)


## Quick Start

1. Make a directory which will be hosting the system as well as all your exams. This directory may contain other directories can contents as well, since the installation process will generate a separate directory ```adam-exam```. Change into this hosting directory. For example:

````
  cd ~username/WORKING
````

2. Clone the github repository into this directory

````
  git clone https://github.com/clecap/adam-exam
````

3. Ensure that this directory is in your LaTeX file search path with recursive searching enabled.
 Implementing this step heavily depends on your LaTeX installation. In my case all local LaTeX sytle files and packages live inside of ```~username/TEX/local```. My texlive installation is configured by default to recursively search ```~username/Library/tex/latex/local```. I have symbolic link from ```~username/Library/tex/latex/local``` to ```~username/TEX/local``` and inside of ```~username/TEX/local``` I have a symbolic link to ```~username/WORKING/adam-exam```

4. For every new exam make a subdirectory inside of the  ```klausuren/``` which in our example resides in ```~username/WORKING/adam-exam/klausuren```

5. To generate the docker image:

```
  cd docker
  docker build -t adam-exam:latest .
  docker compose up
```







## Explanation

Getting the paths correct is important for the following reasons:

* LaTeX has a pretty involved system for searching and including files, which makes it easy to include the wrong files.
* Exams are sensitive materials regarding data protection as well as exam confidentiality.
* The system is built in a way to make the processing transparent and easy to debug. It thus will produce several temporary directories and manages paths by itself. Breaking these assumptions breaks the system.


## Latex Components





## For Graders

Place trusted.js into

<user homedirectory>/Library/Application Support/Adobe/Acrobat/DC/JavaScripts

Add path which contains the grading files to Security (Enhanced) in adobe reader Settings

Security 8Enhanced). Enable Protected mode at startup. Off 
   Enable Enhanced Security: Off


* Preferences -> FullScreen -> Alert when document requests full screen = Off
* Preferences-> Generative AI -> Enable Generative Ai features in acrobat = Off
* Preferences -> General -> Show Online Storgae when opening files = Off
* Preferences -> General -> Show me messages when I launch ... = Off





Click on Save and Next...


When restarting grading, 



# Security

adm-exam must be in the path



Correcting:

In a directory not containing a START.pdf script the files can and must be opened individually AND saved individually (CHECK!!)



