# Description

**Adam-Exam** is a solution for automating

- the generation of printable PDF-based exam sheets and grading schemes
- the scanning, checking, and archiving of exam sheets
- the grading process, especially when distributed among several graders
- the documentation of the grading and evaluation schemes

<details><summary><b  style='font-size:larger'>More Details</b></summary>

**The motivation** for developing Adam-Exam was:

- An increased demand by exam governance bodies for documenting all steps of the examination process.
- An increased demand by examinees to get feedback on their mistakes.
- An increased number of exam participants.
- The closed source and closed process structure of competing commercial solutions, which made it impossible for the examiners to adjust the workflows to their needs and which offered graphical user interfaces with an increasingly intransparent access to the cognitive models behind their solutions.
- As a project for the author for studying the capabilities of Claude and ChatGPT.

**The design decisions** in Adam-Exam favor terminal and script access to the user interface, which makes the system more flexible and adjustable for users capable of using terminal shell commands, Docker containers, and programming languages. They, however, make the system less friendly for users who would prefer easy-peasy graphical interfaces over a tight control of program execution.

</details>

## Instructions for Graders

Grading takes place with the **Adobe PDF Reader**. It uses the JavaScript and form features of that reader. Most other PDF readers are not supported and not tested, they might not work.

<details><summary><b style='font-size:larger'>Basic Workflows</b></summary>

You can use three strategies for grading, which provide varying support for convenience and scalability of your grading work. The strategies may require some adjustment of the preferences of your Adobe PDF Reader.

| Strategy | Scroll to next question <br>to be graded | Open next sheet <br> to be graded |
| -------- | ---------------------------------------- | --------------------------------- |
| Manual   | User                                     | User                              |
| Semi     | Automatic                                | User                              |
| Auto     | Automatic                                | Automatic                         |

</details>

<details><summary><b style='font-size:larger'>Preference Settings for Adobe PDF Reader</b></summary>

##### Manual Strategy
* **Necessary:** Preferences -> JavaScript -> Enable Acrobat JavaScript
* **Recommended:** Preferences -> JavaScript -> JavaScript Debugger -> Show console on errors and messages


##### Semi Strategy
* **Necessary:** All settings for the manual strategy plus:
* **Necessary:** Preferences -> Security (Enhanced) -> Add Folder Path: Select the directory in which the exam sheets reside. (It may also be a parent-directory through several transitive steps).

##### Auto Strategy
* **Necessary:** All settings for the semi strategy plus:
* **Necessary:** Place file ``` js/trusted.js``` into directory 
 ```<user homedirectory>/Library/Application Support/Adobe/Acrobat/DC/JavaScripts```

 This JavaScript file provides some additional trusted functionality to the Adobe PDF Reader.
 The use of these functions is limited to subdirectories of a directory called ```adam-exam```.

Security 8Enhanced). Enable Protected mode at startup: Off
Enable Enhanced Security: Off

- Preferences -> FullScreen -> Alert when document requests full screen = Off
- Preferences-> Generative AI -> Enable Generative Ai features in acrobat = Off
- Preferences -> General -> Show Online Storgae when opening files = Off
- Preferences -> General -> Show me messages when I launch ... = Off

  Restart the adobe PDF Reader when you made these settings.

</details>


<details><summary><b style='font-size:larger'>Manual Grading</b></summary>

</details>



<details><summary><b style='font-size:larger'>Semi Grading</b></summary>

</details>



<details><summary><b style='font-size:larger'>Auto Grading</b></summary>

</details>






<details><summary><b style='font-size:larger'>Calculation of Grades</b></summary>

* The points are summed.
* A percentage is calculated.
* The percentage is rounded using the ceiling function.
* The grade is determined using the following scale:

| Percentage p       | Grade |
| ------------------ | ----- |
| p > 95 && p <= 100 | 1.0   |
| p > 90 && p <= 95  | 1.3   |
| p > 85 && p <= 90  | 1.7   |
| p > 80 && p <= 85  | 2.0   |
| p > 75 && p <= 80  | 2.3   |
| p > 70 && p <= 75  | 2.7   |
| p > 65 && p <= 70  | 3.0   |
| p > 60 && p <= 65  | 3.3   |
| p > 55 && p <= 60  | 3.7   |
| p > 50 && p <= 55  | 4.0   |
| p >= 0 && p <= 50  | 5     |

Adjustments of the grading table can be implemented in file ```js/inject.js``` in function ```gradeToMark```.

When adjusting the grading table: Note that percentages are rounded usign the ceiling function. This can have an effect on the grading table.

</details>

# Installation

## Requirements

1 A working LaTeX compilation environment (I am using Texlive)
2 A working docker installation (I am using Dockerhub)

## Quick Start

1. Make a directory which will be hosting the system as well as all your exams. This directory may contain other directories can contents as well, since the installation process will generate a separate directory `adam-exam`. Change into this hosting directory. For example:

```
  cd ~username/WORKING
```

2. Clone the github repository into this directory

```
  git clone https://github.com/clecap/adam-exam
```

3. Ensure that this directory is in your LaTeX file search path with recursive searching enabled.
   Implementing this step heavily depends on your LaTeX installation. In my case all local LaTeX sytle files and packages live inside of `~username/TEX/local`. My texlive installation is configured by default to recursively search `~username/Library/tex/latex/local`. I have symbolic link from `~username/Library/tex/latex/local` to `~username/TEX/local` and inside of `~username/TEX/local` I have a symbolic link to `~username/WORKING/adam-exam`

4. For every new exam make a subdirectory inside of the `klausuren/` which in our example resides in `~username/WORKING/adam-exam/klausuren`

5. To generate the docker image:

```
  cd docker
  docker build -t adam-exam:latest .
  docker compose up
```

## Explanation

Getting the paths correct is important for the following reasons:

- LaTeX has a pretty involved system for searching and including files, which makes it easy to include the wrong files.
- Exams are sensitive materials regarding data protection as well as exam confidentiality.
- The system is built in a way to make the processing transparent and easy to debug. It thus will produce several temporary directories and manages paths by itself. Breaking these assumptions breaks the system.

## Latex Components

# Security

adm-exam must be in the path

Correcting:

In a directory not containing a START.pdf script the files can and must be opened individually AND saved individually (CHECK!!)
