# Description

**Adam-Exam** is a solution for 

- generating printable PDF-based exam sheets and grading schemes using LaTeX.
- scanning, checking, data-cleansing, and archiving of exam sheets.
- grading exam sheets,  especially when distributed among several graders.
- documenting grading and evaluation schemes.

<details><summary><b  style='font-size:larger'>More Details</b></summary>

**The motivation** for developing Adam-Exam was:

- An increased demand by exam governance bodies for documenting all steps of the examination process.
- An increased demand by examinees to get feedback on their mistakes.
- An increased number of exam participants.
- The closed source and closed process structure of competing commercial solutions, which made it impossible for the examiners to adjust the workflows to their needs and which offered graphical user interfaces with an increasingly intransparent access to the cognitive models behind their solutions.
- A project for the author for studying the capabilities of Claude and ChatGPT.

**The design decisions** in Adam-Exam favor terminal and script access to the user interface, which makes the system more flexible and adjustable for users capable of using 
* LaTeX
* terminal shell commands
* Docker containers, and 
* programming languages. 

They, however, make the system less friendly for users who would prefer easy-peasy graphical interfaces over a tight control of program execution.

</details>


## Instructions for Graders Only

Grading takes place with the **Adobe PDF Reader**. It uses the JavaScript and form features of that reader. Most other PDF readers are not supported or not supported fully; they are not tested, and they might not work.

<details><summary><b style='font-size:larger'>Preference Settings for Adobe PDF Reader (Read me first!)</b></summary>

* Preferences -> JavaScript -> Enable Acrobat JavaScript
* Preferences -> JavaScript -> JavaScript Debugger -> Show console on errors and messages
* Preferences -> Security (Enhanced) -> Add Folder Path: Select the directory in which the exam sheets reside. (It may also be a parent-directory through several transitive steps).
* Place file ```js/trusted.js``` from [this Github Repository https://github.com/clecap/adam-exam](https://github.com/clecap/adam-exam) into the directory which the Adobe PDF Reader uses for trusted JS. This directory can be found on MacOS on this path:
   ```<user-homedirectory>/Library/Application Support/Adobe/Acrobat/DC/JavaScripts```

 This JavaScript file provides some additional trusted functionality to the Adobe PDF Reader.
 The use of these functions is limited to subdirectories of a directory called ```adam-exam```.

  Restart the Adobe PDF Reader (full quit!) after you made these settings.

</details>


<details><summary><b style='font-size:larger'>Grading</b></summary>

1. Make a directory named ```adam-exam``` somewhere on your local machine.
1. Ensure that this folder is listed as trusted under  Preferences -> Security (Enhanced) -> Add Folder Path.

1. Download the entire directory with your name into this directory. This directory should contain:
    1. a directory of the form ```input-<TAG>```, which contains the sheets to be graded.
    1. a directory of the from ```completed-<TAG>```, which contains the sheets which have been graded.  
    1. a file ```queue.txt```, which contains a list of sheets to be graded.
    1. a file ```START.pdf```, which **always** is the entry point into the grading process.

1. Open the file ```START.pdf``` with Adobe Reader and follow the instructions.

**Pausing:** You can pause and restart the grading process at any time. When restarting, again open ```START.pdf```

**Finished:** When you have completed the grading, all graded sheets reside in the subdirectory ```completed-<TAG>/```.  
Upload this subdirectory to the server.

**Correcting:** When you want to correct a grading: 
1. Delete the incorrectly graded file in directory ```completed-<TAG>/```
1. Open ```START.pdf``` and follow the instructions.
</details>



<details><summary><b style='font-size:larger'>Possibilities for Grading</b></summary>

**Item grading:**
* Following the provided solution items you can provide points by clicking individual items of the solution.
* When all points have been given, or when zero points have been achieved, you close the grading (checkbox: Fertig)

**Bonus / Malus grading:**
* If you like or dislike particular features of the solution, you can provide bonus / malus points.
* Malus points cannot lead to negative points for a question, as according to (German) examination law, a single failed task must not contribute negatively towards the garde of an exam.
* Bonus points and discretionary grading may lead to mor ethan 100% of the points. This also leads to a grade of "1.0" and colors the grade field yellow to draw the attention of the grader to this fact.

**Discretionary grading:**
* If the provided solution does not contain a reasonable dramework for grading the solution, since the student has followed a different path, discretionary grading is possible by entering a numer of points into a text field.
* In this case, none of the other points apply nor the bonus / malus applies.

**Comments:** You can provide optional comments as feedback to the learner.

**Hinting:** The solution can provide optional hints to the learner, particularly for situations where typical errors can be expected
or for situations where typical grading processes might require hints. You can click the hints and thereby show the learner that this hint applies.

**Didactical side remark:** Grading along the lines of prescribed solution items, although highly efficient and scalable for mass exams,didactically is not the optimal form of grading. In this case, you can use discretionary grading and comments, or stop using this system.

</details>


<details><summary><b style='font-size:larger'>Calculation of Grades</b></summary>

* The points are summed.
* A percentage is calculated.
* The percentage is rounded using the ceiling function.
* The grade is determined using the following scale:

| Percentage p       | Grade |
| ------------------ | ----- |
| p > 95             | 1.0   |
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



<details><summary><b style='font-size:larger'>Some Remarks</b></summary>

* The condition of being inside a subdirectory of a directory ```adam-exam/``` ensures that the additional functionality implemented in ```trusted.js``` is available only to PDF files of this application. In this sense, it serves as a security sandbox.
* Some constructions in the workflow are the consequence of the other security mechanisms imposed by Adobe PDF Reader. For example, there is no function for traversing a directory. Thus, the file ```queue.txt```is used.
</details>




## Instructions for 


# Further parts of this readme are still draft status and preliminary

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
