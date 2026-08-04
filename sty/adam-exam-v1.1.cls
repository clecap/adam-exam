\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{adam-exam-v1.1}[2026/07/07 Class for grading exams]

% Author:   Clemens H. Cap  clemens@clemens-cap.de
% License:  

%%
%% Load Base Class
%%
\LoadClass[11pt,a4paper]{exam}       % we use some elements of the exam class

%%
%BEGIN_FOLD Load Packages
%%
\usepackage[most]{tcolorbox}
\usepackage{csquotes}                % Want to have this available as author
\usepackage{geometry}                % Better control over the geometry
\usepackage{changepage}              % adjust the margins in the footer
\usepackage{atbegshi}                % Need hook \AtBeginShipout
\usepackage{tikz}                    % For the rounded title box
\usetikzlibrary{calc}                % Used in form generation macro
\usepackage{afterpage}
\usepackage{qrcode}                  % Needed to print QR codes
\usepackage{lipsum}                  % For testing
\usepackage{marginnote}              % Better than marginpar, for margin elements
\usepackage{etoolbox}                % For defining further macros
\usepackage{zref-savepos}            % to record positions
\usepackage{zref-abspage}
\usepackage{zref-user}               % Fixes broken \thepage for large minipages
\usepackage{atbegshi}                % for page coordinates
\usepackage{comment}                 % for commenting out parts
\usepackage[ngerman,english]{babel}
\usepackage{multicol}
\usepackage{xcolor}                   % color names
\usepackage{tabto}
\usepackage[absolute,overlay]{textpos}
\usepackage{pdfpages}                % For pdf form inclusion
\usepackage{insdljs}

\usepackage{hyperref}
\hypersetup{pageanchor=false}        % do not generate page anchors - prevents errors for duplicate page anchros due to reuse of page numbers 

\usepackage{eforms}                  % for PDF form elements with more capabilities than hyperref
\usepackage{totcount}                % We need the sum of all points already at the beginning of the document
\usepackage{xparse}
\usepackage{expl3}                   % For the repetition 
\usepackage{array}
\usepackage{eso-pic}                 % For adding the middle line in the corrections
\usepackage{pifont}                  % for proper radio button symbol
%%\usepackage{draftwatermark}          % For watermark type of marking
%END_FOLD

%%
%BEGIN_FOLD Load own style files
%%
\input{../../../../sty/sevenseg.sty}                % Implements a 7-segment form
\input{../../../../sty/dyncounter.sty}                  % Implements dynamic counters
%END_FOLD


%%
%BEGIN_FOLD Define parameters
%%
\hypersetup{pdfpagemode=UseNone}          % keep bookmark panel in acrobat reader closed

\definecolor{darkgreen}{rgb}{0.0, 0.5, 0.0} % not defined 
%END_FOLD


%%
%% BEGIN_FOLD   Some internal helpers
%%

% Modify macro qrcode so that it is non-clickable (with hyperref loaded)


\makeatletter

\newcommand{\nqrcode}[2][]{%
  \begingroup
    \let\href\@secondoftwo
    \let\hyperlink\@secondoftwo
    \qrcode[#1]{#2}%
  \endgroup
}

%END_FOLD



%%
%% BEGIN_FOLD   DEFINE COUNTERS


\newcounter{pointnum}%          Counter for the point number fields
\newcounter{quest}%             Used for counting the questions
%\refstepcounter{quest}%         Inform latex that this counter will be used for references as well

\newcounter{serial}%            Provides a serial number for the individual exam sheets
\newcounter{totalpoints}%       Counter to keep track of total points

%\regtotcounter{totalpoints}%    Register this counter to package totcount

\newcounter{totalpointsfromfile}%    Number of total points as stored in file

\newcounter{hintbox}%          Counter providing a unique number for hintboxes per solution
\newcounter{chkbox}%           Counter providing a unique number and identification for all checkboxes


\newcounter{shippedpages}% pages shipped in the whole PDF; 0 until the first shipout
\AtBeginShipout{%
  \stepcounter{shippedpages}%                         one step per shipped page
  \immediate\write\@auxout{%                           record the running total in the .aux
    \string\gdef\string\TotalShipped{\arabic{shippedpages}}%
  }%
}%
% Current page's 1-based index, for running headers/footers.
% The head is composed *before* this page's shipout increment, so the
% counter is always one behind the page being built; +1 corrects that.
\newcommand{\ShippedPages}{\the\numexpr\value{shippedpages}+1\relax}%
\providecommand{\TotalShipped}{??}%                   final total; filled from .aux on the 2nd compile



\def\initAllCounters{%                               Initialize counters to the begining of one complete exam package
  \setcounter{pointnum}{1}%
  \setcounter{quest}{1}%
  \setcounter{page}{1}%
  \stepcounter{serial}%
  \setcounter{totalpoints}{0}%
}



\ExplSyntaxOn
\int_new:N \g_max_page_int

% Tracks whether \savedmaxpage holds a real number from a previous run's
% .aux file, as opposed to the non-numeric placeholder below -- needed
% because \int_compare:nNnF further down can't be used on the placeholder.
\bool_new:N \g_savedmaxpage_isreal_bool

% \savedmaxpage is only defined once the .aux file from a previous run has
% been read in. On the first run (or after deleting the .aux file) it
% doesn't exist yet, so provide a placeholder here -- after the .aux file
% has been read (\begin{document} has already run) but before the header
% is typeset on page 1 -- and let the real \gdef from the .aux file
% override it on subsequent runs.
\AtBeginDocument
  {
    \cs_if_exist:NTF \savedmaxpage
      { \bool_gset_true:N \g_savedmaxpage_isreal_bool }
      { \cs_gset:Npn \savedmaxpage { ???? } }
  }


% After each page is shipped out, update \g_max_page_int to the highest
% page number seen so far, since the final page count isn't known until
% the document has been fully typeset.
\AddToHook{shipout/after}
  {
    \int_gset:Nn \g_max_page_int
      { \int_max:nn { \g_max_page_int } { \value{page} } }
  }



  
% At the end of the run, persist the max page count to the .aux file as
% \savedmaxpage so it's available on the next run, and warn to rerun LaTeX
% if that saved value doesn't match this run's count (i.e. it's now stale).
\AtEndDocument
  {
    \iow_now:Nx \@auxout
      { \string\gdef\string\savedmaxpage{\int_use:N \g_max_page_int} }

    \bool_if:NT \g_savedmaxpage_isreal_bool
      {
        \int_compare:nNnF
          { \savedmaxpage } = { \g_max_page_int }
          {
            \GenericWarning{}{Rerun LaTeX to get cross-references right}
          }
      }
  }

% Public command exposing the final total page count, e.g. for use in
% headers/footers ("Page X of \MaxPageNumber").
\NewDocumentCommand{\MaxPageNumber}{}{\int_use:N \g_max_page_int}


\ExplSyntaxOff


%% END_FOLD



\newbool{showbuttons}
\newbool{entermatrikel}
\newbool{showsummation}

\newbool{buildingCorrections}%  flag indicating that we are building correction sheets; effect: print a \CheckBox{}
% NOTE: we need this construction since in the NORMAL run we want to add points but we do not want to set checkboxes
%       however, hyperref generates references somewhere and they then would be undefined and produce warnings

\makeatletter


%%
%% BEGIN_FOLD  API / MACROS for typesetting the exam
%%

%
% \cb    Checkbox Macro (for number of points in an answer)
%
% First parameter:    Number of points, if missing defaulting to 1; must be larger or equal than 1
% Second parameter:  Text which is displayed in specific markup to provide better connection with certain parts of the answer.



\newcommand{\cb}[1][1]{%
  \count@=#1\relax%         Pick up first argument, number of points
  \ifnum\count@=0\relax
    \PackageError{mycheckbox}{Optional argument must be an integer > 0 (got '#1')}{Use \string\zb or \string\hb for 0 points.}%
  \fi
  \ifnum\count@<0\relax
    \PackageError{mycheckbox}{Optional argument must be an integer > 0 (got '#1')}{Use \string\cb[1] or larger.}%
  \fi
  \edef\cbmyval{\number\count@}%
  \stepcounter{chkbox}%  Increment counter of all checkboxes ensures unique numbering
  \AddDynCounter{cbcount}{\thequestion}{\cbmyval}%
  \space
  \ifinlist{\currentQuestion}{\my@grading}{\def\readonlyflag{false}\def\bordercolor{1 0 0}\def\textcolor{red}}{\def\readonlyflag{true}\def\bordercolor{0 0 0}\def\textcolor{black}}% set the proper read only flag
  %
  \ifbool{showsummation}{%
    \CheckBox[name=\currentQuestion X\thechkbox-\myexamserial,width=14bp,height=14bp,borderwidth=2,borderstyle=S,bordercolor=\bordercolor,readonly=\readonlyflag,validate={injectValue(\currentQuestion,"\myexamserial", event, \cbmyval);},onmouseup={pointClick(\currentQuestion,"\myexamserial", event, \cbmyval);}]{}%
  }%
  {}%
%
%
  {\space\color{\textcolor} (\cbmyval\ Pkt)}%
  \hspace*{0.3cm}%
  \@ifnextchar\bgroup{\cb@get}{}%
}




%
\newcommand{\cb@get}[1]{
  {%  Need to open local scope for the color
    \color{blue}%
    \noindent\parbox{0.8\linewidth}{#1}%
  }
}


% \hb    Hint Box for typesetting a hint while grading
% First and only, mandatory parameter: Text of the hint
% A hint has no effect on the number of points
% a hint box has an H as part of the id
\newcommand{\hb}[1]{
  \stepcounter{hintbox}%  Increment counter of all checkboxes ensures unique numbering
  \ifinlist{\currentQuestion}{\my@grading}{\def\readonlyflag{false}\def\bordercolor{1 0 0}\def\textcolor{red}}{\def\readonlyflag{true}\def\bordercolor{0 0 0}\def\textcolor{black}}% set the proper read only flag
  \mbox{\CheckBox[name=H\currentQuestion-\thehintbox-\myexamserial,width=14bp,height=14bp,borderwidth=2,borderstyle=S,bordercolor={0 0 0},readonly=\readonlyflag]{}}% \mbox ensures proper handling of height
  \hspace*{0.3cm}
  \noindent\parbox{0.8\linewidth}{\textbf{Hint:} #1}
}


%% Define a block which can be used as bonus / malus adjustment
%%
\def\bonusmalus{
  {\small\begin{tabular}[]{@{}c}Bonus\\Malus\end{tabular}}
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,readonly=\readonlyflag,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{+3}\hspace*{0.2cm}% default key and readlonly must be first in group
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{+2}\hspace*{0.2cm}%
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{+1}\hspace*{0.2cm}%
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{0}\hspace*{0.2cm}%
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{-1}\hspace*{0.2cm}%
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{-2}\hspace*{0.2cm}%
  \ChoiceMenu[radio,radiosymbol=\ding{108},name=grp\currentQuestion-\myexamserial,bordercolor=\bordercolor,onmouseup={radioChange(\currentQuestion, "\myexamserial", event);}]{}{-3}\hspace*{0.2cm}%
}

%%
%% Defines a block for discretionary points
%%
\def\discretionarypoints{
  {\small\begin{tabular}[]{@{}cc}Freie\\Wertung\end{tabular}}
  \raisebox{-6pt}{\mbox{\TextField[name=D\currentQuestion-\myexamserial,width=0.7cm,height=0.6cm,bordercolor=\bordercolor,borderwidth=2,charsize=12pt,readonly=\readonlyflag,onblur={onblur(\currentQuestion,"\myexamserial",event);},keystroke={numericKS(\currentQuestion,"\myexamserial",event);},validate={numericValidate(\currentQuestion, "\myexamserial",event);}]{}}}
}

% \zb   Zero Box for typesetting a 
%       (1) "checked this task and there are no points to be awarded"
%       (2) "checked this task and max points available can be awarded"
%       (3) "ad libitum"
% Needed for distinguishing ungraded questions from graded questions with zero points
\newcommand{\zb}{
  \ifinlist{\currentQuestion}{\my@grading}{\def\readonlyflag{false}\def\bordercolor{1 0 0}\def\textcolor{red}}{\def\readonlyflag{true}\def\bordercolor{0 0 0}\def\textcolor{black}}% set the proper read only flag
  %
  \mbox{\CheckBox[name=Z\currentQuestion-\myexamserial,width=14bp,height=14bp,borderwidth=2,borderstyle=S,bordercolor=\bordercolor,readonly=\readonlyflag,onmouseup={completedClick(\currentQuestion,"\myexamserial", event);}]{}}% \mbox ensures proper handling of height
  %
  \hspace*{0.2cm}% \parbox{0.2\linewidth}{{\color{red}\textbf{Bewertet}} }% 
  {{\color{\textcolor}\textbf{Fertig}}}
  %
%  BUTTON FO ACTIVATING ALL
%  \hspace*{0.6cm}%
%  \mbox{
%  \PushButton[name=A\currentQuestion-\myexamserial,height=1.0cm,width=3cm,bordercolor=\bordercolor,color={red},borderwidth=2,
%    onblur={buttonFocusOff(event)},onfocus={buttonFocusOn(event)},
%    readonly=\readonlyflag,onclick={ allButton(\currentQuestion,"\myexamserial",event); } ]{\color{\textcolor} ALL}
%  }
  %
  %
  \hspace*{1cm}
  \bonusmalus
  \hfill
  {\Large\color{\textcolor}\underline{\bf x}or}
  \hspace*{1cm}
  \discretionarypoints
  %
  %
}






\newcommand{\commentfield}{%
 \raisebox{12pt}{\small%
 \begin{tabular}[]{@{}l}
 Optional \\
 Comment
 \end{tabular}}
 \mbox{\TextField[
    name={\currentQuestion C-\myexamserial},
    width=19.0cm,
    height=1.0cm,
    multiline=true,
    bordercolor={0 0 0},
    backgroundcolor={1 1 1},
    charsize=10pt,
    default={}
  ]{}}%
}

%\renewcommand{\zb}{}%              Take out for debugging
%\renewcommand{\commentfield}{}



%
%
% environment for typesetting several copies of an exam
%
% \begin{copies}{10}   ...  \end{copies}
%
\NewEnviron{copies}[1]{%
%
%
  \global\def\myTotalExams{#1}
  \foreach \n in {1,...,#1}{%
    \BODY%
    \ifnum\n<#1\newpage\fi%
  }%
}

\global\def\myTotalExams{1}%           define counter also outside of a copies environment



% END_FOLD



% File into which the coordinates of the point fields gets written
\newwrite\coordfile
\immediate\openout\coordfile=\jobname.crd

% File into which the commands writing the solutions get written
\newwrite\solfile
\immediate\openout\solfile=\jobname.sol



% There is too much space after the onepar checkbox environment of exam. Correct for this.
\apptocmd{\endoneparcheckboxes}{\vspace{-\topsep}}{}{}




%%
%% User Interface for this class
%%


% Writes to a file the command which shall later generate the point form for a task
% Arg 1: Number of the question as part of the exam
% Arg 2: Number of the page where this question appears in this exam
% Writes the positions for the boxes to external file
\def\writePointform#1#2{%
  \zsavepos{#1}%
  \immediate\write\coordfile{\noexpand\pointform{\the\dimexpr\hoffset+0.7cm+\textwidth}{\the\dimexpr\paperheight-\zposy{#1}sp}{#1}{#2}}%
}





% Writes to a file the command which shall later generate the solution information for a task
% Arg 1: Number of the question as part of the exam
% Arg 2: Number of the page where this question appears in this exam
% Arg 3: The solution
\long\def\writeSol#1#2#3{
  \zsavepos{SOL#1}%    save the curent position under mark SOL<number-of-question|
  \immediate\write\solfile{\noexpand\provideAnswer{#1}{#2}{#3}   {\the\dimexpr\paperheight-1.3cm-\zposy{SOL#1}sp}}
}
  
  


% if first argument equals the current page, we print the second argument
% otherwise we do nothing
\newcommand{\ifpage}[2]{%
  \ifnum\value{page}=#1 %
    #2 %
  \fi
}





% Defines a helper drawing a box which we will draw around an answer area
\newtcolorbox{my@answerbox}[1]{%
  enhanced,
  %width=0.5\linewidth,
  colframe=black,
  colback=white,
  boxrule=0.6pt,
  arc=3mm,                 % Abrundung der Ecken
  fonttitle=\bfseries\color{black},
  title=#1,                % Titeltext
  attach boxed title to top center={yshift=-\tcboxedtitleheight/2}, % Titel "in" die Linie
  boxed title style={%
    colframe=white,        % kein Rahmen um den Titel
    colback=white,         % Hintergrund des Titels = Seitenhintergrund
    left=2mm,
    right=2mm
  }
}



%%
%% API CALL:  \aa{ <Text used for the answer area> }
%%
\renewcommand{\aa}[1]{%
  \begin{my@answerbox}{Bereich für die Antwort / Answer Area}
    \medskip #1 
  \end{my@answerbox}%
}


%%
%% API CALL: Provide meta data for the exam
%%
%%   \exam{ <name of exam> }
%%   \duration{ <duration of exam> }
%%   \place{ <place of exam> }
%%   \date{ <date of exam> }
%%
\newcommand{\exam}[1]{\def\my@exam{#1}}%  legacy

\newcommand{\duration}[1]{\def\my@duration{#1}}
\newcommand{\place}[1]{\def\my@place{#1}}
\renewcommand{\date}[1]{\def\my@date{#1}}

\newcommand{\examSerial}[1]{\def\myexamserial{#1}}
\newcommand{\examId}[1]{\def\my@exam@id{#1}}
\newcommand{\examTitle}[1]{\def\my@exam{#1}}

\newcommand{\source}[1]{\def\mysource{#1}}% Typesetting a source for the answer

\newcommand{\grading}[2]{\def\my@grading{#1}\def\my@grader{#2}}




%%
%%BEGIN_FOLD  Formatting the solutions area
%%


%%
%% Fixing the line filler command
%%

% We will exchange the old \fillwithlines macro from exam by a more sophisticated functionality
% But we still need the original one. So first rename the original one to something else
\let\originalfillwithlines\fillwithlines

% the normal, original command fillwithlines misbehaves if we are inside of a list-type environment
% we define a new command which corrects for this misbehaviour 
\newcommand{\fillwithlinesunderlabel}[1]{%
  \par% ensure we are in vertical mode % this could be required in some cases
  {\hspace*{-\dimexpr\labelwidth+\labelsep\relax}%
   \advance\linewidth by \dimexpr\labelwidth+\labelsep\relax
   \vspace*{-0.5cm}%                 Move it up a bit
   \originalfillwithlines{#1}}%
}


% Now build a Conditional dispatcher calling one or the other
\newcommand{\switchingfillwithlines}[1]{%
  \setlength{\linefillheight}{20pt}
  \begingroup
    \ifnum\@listdepth>0\relax
      \fillwithlinesunderlabel{#1}%
    \else
      \originalfillwithlines{#1}%
    \fi
  \endgroup
}




% Now we define a macro which draws a specified number of lines
% This only works outside of lists such as enumerate

%\newcommand{\DrawLinesNormal}[1]{%
%  \par
%  \begingroup
%    \dimen0=20pt      % distance between successive lines
%    \dimen2=0.1pt     % rule thickness
%    \offinterlineskip
%    \vskip \dimen0
%    \count0=#1\relax
%    \loop\ifnum\count0>0\relax
%      \noindent\hrule height \dimen2 width \linewidth\relax
%      \advance\count0 by -1\relax
%      \ifnum\count0>0\relax
%        \vskip \dimen0\relax
%      \fi
%    \repeat
%  \endgroup
%}



\newlength{\DrawLinesSep}
\setlength{\DrawLinesSep}{20pt}

\newlength{\DrawLinesThickness}
\setlength{\DrawLinesThickness}{0.1pt}

% Draw Lines which works in normal paragraph
\newcommand{\DrawLinesNormal}[1]{%
  \par
  \begingroup
    \offinterlineskip
    \vskip\DrawLinesSep
    \count0=#1\relax
    \loop\ifnum\count0>0\relax
      \noindent
      \hrule height\DrawLinesThickness width\linewidth\relax
      \advance\count0 by -1\relax
      \ifnum\count0>0\relax
        \vskip\DrawLinesSep
      \fi
    \repeat
  \endgroup
}


% Draw Lines which works in lists.
\newcommand{\DrawLinesInList}[1]{%
  \leavevmode
  \par
  \nobreak
  \nointerlineskip
  \begingroup
    \offinterlineskip
    \count0=#1\relax
    \loop\ifnum\count0>0\relax
      \noindent\rule{\linewidth}{\DrawLinesThickness}\par
      \advance\count0 by -1\relax
      \ifnum\count0>0\relax
        \vskip\DrawLinesSep\relax
      \fi
    \repeat
  \endgroup
}



\newcommand{\DrawLines}[1]{%
  \ifnum\@listdepth>0\relax
    \DrawLinesInList{#1}%
  \else
    \DrawLinesNormal{#1}%
  \fi
}


\newcommand{\DrawLinesRest}{%
  \fillrestwithlineshelper\DrawLinesSep%
}




% Now a helper function which allows to fill the remaining space of the page
% with lines of a certain thickness in certain distance and leaving a bit of space below
% This is a helper to adjust for \fillrestwithlines
% Fill the remaining space on the current page with horizontal lines.
% #1 = line spacing (optional, default \baselineskip)
% #2 = space to leave at bottom of page (optional, default 1\baselineskip)
\newcommand{\fillrestwithlineshelper}[2][\baselineskip]{%
  \vspace*{1.0cm}%
  \begingroup
    \dimen0=\pagegoal
    \dimen2=0.1pt
    % If \pagegoal is not usable here, fall back to \textheight.
    \ifdim\dimen0>1000pt\relax
    \else
      \dimen0=\textheight
    \fi
    \dimen0=\dimexpr\dimen0-\pagetotal-#2\relax
    \ifdim\dimen0<0pt \dimen0=0pt\fi
    \vbox to \dimen0{%
      \offinterlineskip
      \leaders\vbox{%
        \hrule width \linewidth height \dimen2
        \vskip #1
      }\vfill
    }%
  \endgroup%
  \vspace*{-0.5cm}%  aesthetic correction
}


\newcommand{\fillrestwithlines}{\fillrestwithlineshelper[20pt]{4.1cm}}


\ExplSyntaxOn

% Stubs
%\newcommand{\FILLNOARG}{Called with no argument}
%\newcommand{\FILLINTEGER}[1]{Called with an integer~#1}
%\newcommand{\FILLENGTH}[1]{Called with a length~#1}

\ExplSyntaxOn

% \FILL:
% - if next token is { ... } -> dispatch on its contents
% - otherwise -> no-argument case
\NewDocumentCommand{\FILL}{}{
  \peek_meaning:NTF \c_group_begin_token
    { \__my_fill_with_brace:w }  % next token is { -> read it
    { \fillrestwithlines }       % CASE 1:   no argument given at all
}

% read one braced argument and dispatch on it
\cs_new_protected:Npn \__my_fill_with_brace:w #1
  { \__my_fill_dispatch:n { #1 } }

% Existing dispatcher for the "argument provided" case
\cs_new_protected:Npn \__my_fill_dispatch:n #1
  {
    \regex_match:nnTF { \A \s* \d+ \s* \Z } { #1 }
      { \DrawLines{#1} }
      {
        \__my_length_if_valid:nTF { #1 }
          { \switchingfillwithlines{#1} }
          { \msg_error:nnn { myfill } { invalid-arg } { #1 } }
      }
  }

% Portable "is this a length?" test:
\cs_new_protected:Npn \__my_length_if_valid:nTF #1#2#3
  {
    \group_begin:
      \cs_set_protected:Npn \__my_tmp_do_error:nn ##1##2
        { \group_end: \use_ii:nn {#2} {#3} }
      \cs_set_eq:NN \__my_saved_error:nn \msg_error:nn
      \cs_set_eq:NN \msg_error:nn \__my_tmp_do_error:nn
      \setlength{\@tempdima}{#1}%
      \cs_set_eq:NN \msg_error:nn \__my_saved_error:nn
    \group_end:
    #2
  }

\msg_new:nnn { myfill } { invalid-arg }
  { Invalid~argument~'#1'.~Use~an~integer~(e.g.~5)~or~a~length~(e.g.~2cm). }

\ExplSyntaxOff



%END_FOLD







%%
%% Set some formatting for the exam format
%%
\def\setExamFormatting{
  %
  \parskip 0.25cm
  \parindent 0pt 
  %
    \def\@listi{%
      %\leftmargin=0pt
      %\itemindent=0pt
      %\labelsep=0.5em
      %\labelwidth=0pt
      %\listparindent=0pt
      \parsep=0pt
    % % \topsep=0pt
    % % \partopsep=0pt
    % % \itemsep=0pt
      }%
      \let\@listI\@listi
  %
  % Turn on header/footer style
  \pagestyle{headandfoot}
  %
  % Define header
  %
  %\firstpageheader{Page\ \thepage\ of \savedmaxpage\ in exam \theserial}{\tiny \ShippedPages / \TotalShipped}{Exam \theserial\ of \myTotalExams\hspace*{2cm}}
  \firstpageheader{Page\ \thepage\ of \savedmaxpage\ in exam \theserial}{\tiny \ShippedPages / \TotalShipped}{Exam \theserial\ of \myTotalExams}
  \runningheader{Page\ \thepage\ of \savedmaxpage\ in exam \theserial}{\hspace*{2cm}\tiny \ShippedPages / \TotalShipped}{Exam \theserial\ of \myTotalExams\hspace*{-2cm}}  
  %
  % Define footer
  %
  \def\lfooter{\nqrcode[height=2.5cm,level=H]{P\arabic{page}} \linebreak \texttt{P\arabic{page}}}       % Define the left footer qr b, for the page number
  %
 \def\rfooter{ \def\dist@Twist{15.0cm}%   ADJUST this to get the distance of the right QR box matching to the geometry 
    \makebox[\dist@Twist][r]{\nqrcode[height=2.5cm,level=H]{S\arabic{serial}}}\space%  NOTE: Need a \space here for the next box to show properly
    \makebox[\dist@Twist][r]{\texttt{S\arabic{serial}}}%
  }
   \def\cfooter{\hspace*{4cm}
            \begin{tabular}[]{@{}ll}
              {\bf Max. Points:\space \thetotalpointsfromfile} \\
              Bestanden: Mehr ($>$) als $50\%$  \\
              Passed: More than ($>$) $50\%$  \\
              Benötigte Punkte: \the\numexpr(\value{totalpointsfromfile}+1)/2\relax  \\
              Required points: \the\numexpr(\value{totalpointsfromfile}+1)/2\relax 
            \end{tabular}}
  
    \firstpagefooter{\lfooter}{}{% We need different layout for the running footer due to the different geometry on these pages
        \def\dist@Twist{15.0cm}%   ADJUST this to get the distance of the right QR box matching to the geometry 
        \makebox[\dist@Twist][r]{\nqrcode[height=2.5cm,level=H]{S\arabic{serial}}\hspace*{2cm}}\space%  NOTE: Need a \space here for the next box to show properly
        \makebox[\dist@Twist][r]{\texttt{S\arabic{serial}}\hspace*{2cm}}%
    } %% End runningfooter
  
  % We need different layout for the running footer due to the different geometry on these pages
  \runningfooter{\lfooter}{\cfooter}{\rfooter} 
  %
  \extrafootheight{4cm}   % Reserve extra space for the tall footer
}%   end set exam formatting







\newcommand{\allpoints}{%
  %\marginnote{%
  \vspace*{1cm}
  \begin{center}
    \parbox[b][1cm][t]{2.6cm}{%
    \begin{tabular}[]{@{}c} \bf Summe \\ \bf Total \\ (\bf max \thetotalpointsfromfile) \end{tabular}}%
     \setlength{\fboxrule}{1pt} % Adjust the thickness of the frame
    \framebox[2cm][c]{\rule{0pt}{1cm}}\parbox[b][1cm][c]{2cm}{}
  \end{center}
  %}%
}

% for minipages which are so large that the layout mechanism pushes them
% to the next page the page counter is off by one and this thing patches this
% #1 is a label for suitable storage of information
% helper: print abspage if known, ?? otherwise (first run)

\newcommand{\AbsPage}[1]{%
  \zref@ifrefundefined{#1}{??}{\zref@extract{#1}{abspage}}%
}



%% Argument 1:   Title:        Text serving as title of the question
%% Argument 2:   Question:     Textual material used for posing the quetion
%% Argument 3:   Answer field: Textual material used for typesetting the answer area
%% Argument 4:   Correction:   Textual material used in the Correction/Solution/Grading area
\NewDocumentEnvironment{question}{+m +m +m +m}
{%
  \setcounter{hintbox}{0}%
  \SetDynCounter{cbcount}{\thequestion}{0}%   Initialize a checkbox point counter for the current question to 0
  \setbox0=\vbox{\def\currentQuestion{} #4}% Execute the correction contents - but without really typesetting it. set currentQuestion undefined for purposes of counting \cg macros here
  \begin{minipage}{\linewidth}%
  \begin{minipage}{\linewidth} \parindent 0pt \parskip 0.25cm %
    {\Large \textbf{\thequest. Frage:} #1} \par%                                 #1 Titel    
      \ifnum\value{serial}=1%                          Only for serial number 1 write the solution information to file sol, since we only need page displacements for the very first serial number
        \zlabel{ara:\arabic{quest}}%                   needed to store the page counter value for minipagepage
        \writeSol{\thequest}%
          {\AbsPage{ara:\arabic{quest}}}%
          {\detokenize{#4} \detokenize{\par\commentfield} \detokenize{\par\zb}    \detokenize{\setcounter{chkbox}{0}}  }%
          % at the end of every soliution: reset the chkbox counter
      \fi%
    #2 %
    \aa{#3}%
%    \zlabel{ara:\arabic{quest}}% needed to store the page counter value for minipagepage
    %% NOW add the point information and write the coordinate file
    \marginnote{%
      \ifnum\value{serial}=1%
        \writePointform{\thequest}{\AbsPage{ara:\arabic{quest}}}%    Save position and generate command which will later in the correction produce a field
      \fi%
      \begin{tabular}[]{@{}l} \GetDynCounter{cbcount}{\thequestion} Punkte \\ \GetDynCounter{cbcount}{\thequestion} Points 
        \\ \framebox[1.8cm][c]{\rule{0pt}{0.6cm}} \end{tabular}%
    }[-2.5cm]%
    \addtocounter{totalpoints}{\GetDynCounter{cbcount}{\thequestion}}%   Add to total points
    \bigskip%
  \end{minipage}%
  \stepcounter{quest}%              Increase the question numer   
  \end{minipage}%
}%
{\ignorespacesafterend}%     Crucial to prevent insertion of unwanted vertical material





%%
%% Contents announcing the empty notepage and informing that this will not be graded
%%
\def\emptypagecontents{%
  \textbf{Leere Seite}, die Sie für Skizzen, Vorbereitungen und eigene Überlegungen nutzen können.\\
  \textbf{Wichtig:} Die Inhalte dieser Seite werden nicht gewertet.

  \textbf{Empty note page} which you can use for sketches, preparations and own thoughts. \\
  \textbf{Important:} The contents of this page will not be graded or read by the graders.
}


%%
%% \emptypage  Typeset a notepage with a non-grading disclaimer
%%
\def\emptypage{%
  \clearpage%
  \emptypagecontents%
  \vfill%
  \newpage%
}



%%
%%
%%
\newcommand{\adjustfordoublesidedprinting}{%
  \clearpage%             Switch into vertical mode
  \ifodd\value{page}%     If we are on an odd page number do nothing
  \else%
    \emptypagecontents%        or \null       Null content, needed to force a page to exist
    \newpage%
  \fi%
}



%%
%% Typeset the exam title
%%
\def\examtitle{%
  \begin{center}\textbf{\Large\my@exam}\end{center}
  \textbf{Dauer:} \my@duration \hspace{0.5cm}   \textbf{Ort:} \my@place \hspace{0.5cm}  \textbf{Datum:} \my@date
}


%%
%% Typeset a signature area for the exam
%%
\def\examsignature{%
  \textbf{\Large Unterschrift / Signature}: \leaders\hrule height 0.4pt\hfill\kern0pt\par%
  \bigskip%
  \textbf{\Large Name}:        \rule{7cm}{0.4pt}%
  \textbf{\Large Matrikel}:    \leaders\hrule height 0.4pt\hfill\kern0pt%
}



\def\examdisclaimer{
 \begin{multicols}{2}
     \small
     \headerDeutsch 
     \par
     \headerEnglish
     \normalsize
  \end{multicols}
}

%%
%%  Typeset a pleas wwait notice
%%
\def\pleasewait{%
  \begin{center}%
    \begin{tabular}[]{@{}c}%
      \mbox{\large\bf\color{red} BLATT NOCH NICHT UMDREHEN}
      \mbox{\large\bf\color{red} WIR STARTEN GEMEINSAM}               \\[10pt] 
      \mbox{\large\bf\color{red} DO NOT TURN THE PAGE}           
      \mbox{\large\bf\color{red} WE ARE STARTING AT THE SAME TIME}
    \end{tabular}%
  \end{center}%
}



\def\matrikelpage{
  Bitte tragen Sie in die ganz unten in grau angedeuteten 9 Felder Ihre Matrikelnummer ein. Nutzen Sie dabei die Siebensegment-Anzeigen
  wie in dem folgenden vorgegebenen Muster. Das erleichtert uns die Arbeit beim Einscannen.\par
%
  Please enter your student registration number into the 9 grey fields in the footer of the page. Use the seven segment notation
  as in the given samples. This makes scanning easier.\par
%
  {\Large\bf Muster -- Sample} \par
%
  \begin{tabular}{c c c c c}
    \sevensegdigit{0} &
    \sevensegdigit{1} &
    \sevensegdigit{2} &
    \sevensegdigit{3} &
    \sevensegdigit{4} \\
    \sevensegdigit{5} &
    \sevensegdigit{6} &
    \sevensegdigit{7} &
    \sevensegdigit{8} &
    \sevensegdigit{9}
  \end{tabular}
%
  \vfill
%
  {\Large\bf Matrikelnummer hier eintragen -- Enter numbers below}\\
%
  \sevensegguide\hspace{2mm}\sevensegguide\hspace{2mm}\sevensegguide\hspace{2mm}\sevensegguide
  \hspace{2mm}
  \sevensegguide\hspace{2mm}\sevensegguide\hspace{2mm}\sevensegguide\hspace{2mm}\sevensegguide\hspace{2mm}\sevensegguide
}%% END \matrikelpage




\input{../../../../customize/disclaimer.tex}



\extrafootheight{4cm}   % Reserve extra space for the tall footer


\def\makeexam{%


  \newgeometry{top=1.5cm, bottom=5cm, lmargin=2cm, rmargin=2cm}%       Define initial geometry for the first page

  \def\my@grading{}%        empty for makeexam
  \def\my@grader{}%         empty ofr makeexam TODO improve
  \def\myexamserial{}%      empty for makeexam - TODO both of these empty intializations will not be needed when we move the definition of \zb, \hb and more into the correction case only
  
  \initAllCounters

  %  \input{\jobname.test} % this also provides the correct value
  %  \setcounter{totalpointsfromfile}{1833} % This is effective

  \setExamFormatting%    Set formatting in the way we want it for an exam

  \examtitle
  \examdisclaimer
  \examsignature
  \pleasewait


  \newpage
  \newgeometry{top=1.5cm, bottom=5cm, lmargin=2cm, rmargin=4cm,
     marginparwidth=2.5in,
     marginparsep=0.8cm  % amount of horizontal separation of margin from normal text
  }
  \matrikelpage
  \newpage
  
}




\newlength{\upper}%                  Vertical position where the footer forms begin
\newlength{\verticalDistance}%       Vertical distance between footer forms

\setlength{\upper}{260mm}
\setlength{\verticalDistance}{6mm}

\def\footerform{
  \def\startposition{30mm}% adjusting horizontal start
  %%
  %% Conditional block for entering matrikel number
  %%
  \ifbool{entermatrikel}
    {\begin{textblock*}{80mm}(\startposition,\upper)
      Matrikel: \tabto{1.8cm}\TextField[name=matrikel-\myexamserial,width=2.2cm,align=1]{}
    \end{textblock*}}
    {}
 %%
 %% Conditional block for showing summation
 %%
  \ifbool{showsummation}{
%  % Sum field (calculated)
  \begin{textblock*}{80mm}(\startposition,\dimexpr\upper+\verticalDistance\relax)
    Punkte: \tabto{1.8cm}\TextField[name=punktesumme-\myexamserial, readonly=true, width=1cm,align=1]{}
  \end{textblock*}
%  % Sum field (calculated)
  \begin{textblock*}{80mm}(\startposition,\dimexpr\upper+2\verticalDistance\relax)
      Prozent: \tabto{1.8cm}\TextField[name=prozent-\myexamserial, readonly=true, width=1cm,align=1 %, calculate={pointsToPercent();}
       ]{}
  \end{textblock*}
%   % Note
  \begin{textblock*}{70mm}(\startposition,\dimexpr\upper+3\verticalDistance+3mm\relax)
    \textbf{\Large Note:} \tabto{1.8cm}\TextField[name=note-\myexamserial, readonly=true,width=1.5cm,height=0.7cm,charsize=14pt,align=1,borderwidth=4 %, calculate={percentToMark();}
      ]{}
  \end{textblock*} 
  }{}
  %%
  %% Conditional block for showing navigation buttons
  %%
  \ifbool{showbuttons}{%
 % \begin{textblock*}{70mm}(198mm,260mm)
 % \TextField[name=nextjob,height=1.0cm,width=18cm,readonly=true,bordercolor={yellow},borderwidth=3,onfocus={goFirstIncomplete();}]{\phantom{XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX}}%
 % \end{textblock*}
  \begin{textblock*}{270mm}(198mm,280mm)
    \PushButton[name=locksavenext,height=1.0cm,width=3cm,bordercolor={orange},color={red},borderwidth=3,onclick={ Process ( {lock:true, save: true, close: true, next:true} );}]{\bf Lock, Save \& Next...}
    \hspace*{1cm}%
    \PushButton[name=savenext,height=1.0cm,width=3cm,bordercolor={yellow},color={red},borderwidth=3,onclick={ Process ( {save:true, close: true, next: true} );}]{Save \& Next...}%
    \hspace*{1cm}
    \PushButton[name=skipnext,height=1.0cm,width=3cm,bordercolor={yellow},color={red},borderwidth=3,onclick={ Process ( {close:true, next:true} );}]{Skip \& Next...}
    \hspace*{1cm}
    \PushButton[name=savestop,height=1.0cm,width=3cm,bordercolor={orange},color={red},borderwidth=3,onclick={ Process ( {save: true, close: true} );}]{\bf Save \& Stop}
    \hspace*{1cm}
    \PushButton[name=skipstop,height=1.0cm,width=3cm,bordercolor={yellow},color={red},borderwidth=3,onclick={ Process ( {save: false, close: true} );}]{\bf Skip \& Stop}
  \end{textblock*}   
  \begin{textblock*}{70mm}(198mm,2mm)
    Serial: \myexamserial
  \end{textblock*}%
  }{}     
}


% Helper callback function which writes a point form 
% Contained in .crd file
% Arg 1: x coord where pointform shall be written
% Arg 2: y coord where pointform shall be written
% Arg 3: Question number 
% Arg 4: Page number 
\def\pointform#1#2#3#4{%
  \ifpage{#4}{%                              Relevant only, if we are on the proper page
  %
  \ifinlist{#3}{\my@grading}{\def\readonlyflag{false}\def\bordercolor{1 0 0}\def\textcolor{red}\def\gradervalue{\my@grader}}{\def\readonlyflag{true}\def\bordercolor{0 0 0}\def\textcolor{black}\def\gradervalue{}}% set the proper read only flag
    \begin{textblock*}{60mm}(#1,#2)%
    \TextField[name=punkte#3-\myexamserial,width=1.8cm,height=0.8cm,readonly=true,borderwidth=2,bordercolor=\bordercolor]{}%
    \end{textblock*}%
  }%
}


% helper conditional macro
% Arg 1: a counter
% arg 2: a comma seperated list without any white space between
% Arg 3: an if path
% Arg 4: an else path
% if the counter is 
% \ifinlist{<number>}{<comma-list>}{<true>}{<false>}
\def\ifinlist#1#2#3#4{%
  \def\found{0}%
  \@for\next:=#2\do{%
    \ifnum\next=#1\relax
      \def\found{1}%
    \fi
  }%
  \ifnum\found=1\relax
    #3%
  \else
    #4%
  \fi
}






% Writes the answer into the correction DIN A3 correction form
% Arg 1: Number of the question
% Arg 2: Number of the page where the answer should be written
% Arg 3: Answer which should be written
% Arg 4: y-offset of the answer on the page
\long\def\provideAnswer#1#2#3#4{
  \global\def\currentQuestion{#1}%
  \ifpage{#2}{%  The command only has an effect if we really are on the page the command is addressing
      \node[anchor=south west,inner sep=-36pt] at ($ (current page.south west) + (\HalfPW,-\dimexpr#4-0.3cm\relax) $) {%
        \begin{minipage}[t][\paperheight]{\HalfPW}%
          \parskip 0.25cm\parindent 0pt%   Provide some local formatting inside of the answer area
 %%         \ifinlist{#1}{\my@grading}{\def\gradervalue{\my@grader}}{\def\gradervalue{}}%       
          \ifinlist{#1}{\my@grading}{\def\readonlyflag{false}\def\bordercolor{1 0 0}\def\textcolor{red}\def\gradervalue{\my@grader}}{\def\readonlyflag{true}\def\bordercolor{0 0 0}\def\textcolor{black}\def\gradervalue{}}% set the proper read only flag
          \begin{Form}%
            \section*{{\color{\textcolor} #1. Solution}  %{\it\small\ifinlist{#1}{\my@grading}{Graded by:\my@grader}{You are not grading this question}}
               \hfill\mbox{\TextField[name=grader\currentQuestion-\myexamserial,width=5cm,height=0.6cm,charsize=12pt,readonly,bordercolor=\bordercolor,value={\gradervalue}]{}}%
            }%
            \vspace*{-0.4cm}%
            #3
 %%         \ifdefined\mysource{{\textbf Quelle:} \mysource}\fi
 %
          \end{Form}% 
        \end{minipage}%
      };% end of node
  }% end of \ifpage
}%







% need a bit more space before an enumerate
\BeforeBeginEnvironment{enumerate}{\vspace*{0.4cm}}

% need a bit less space before a \fillwithlines
\pretocmd{\fillwithlines}{\vspace*{-0.5cm}}{}{}

% and a bit more space after a \fillwithlines
\apptocmd{\fillwithlines}{\vspace*{0.3cm}}{}{}








%%
%BEGIN_FOLD *** Define macro \preparecorrection for the correction type of document
%%
\makeatletter







\newcommand{\commonsettings}[0]{
 \geometry{a3paper,landscape,margin=0mm,left=0mm,right=0mm}%
  \edef\my@filename{\my@exam@id}
  % We must include
  %  total points file
  %  file containing the solutions / corrections
  %  file containing the positions of the correction boxes
  \edef\corfile{\my@exam@id.tot}%
  \typeout{*** preparecorrection: trying to input '\corfile'}%
  \IfFileExists{\corfile}{\input{\corfile}}{\errmessage{Fatal error: required file '\corfile' not found}}
%
%%
%% Precompute some dimensions (avoid .5\paperwidth etc. in keyvals)
%%
  \newdimen\HalfPW
  \newdimen\QuarterPW
  \HalfPW=\dimexpr\paperwidth/2\relax
  \QuarterPW=\dimexpr\paperwidth/4\relax

  \setcounter{pointnum}{1}

  % Patch the enumerate environment a bit to make nice aligned click lists.
  \makeatletter
  \AtBeginDocument{%     TODO      UNIF> for exam and correction ????
  % Level-1 lists (enumerate/itemize) in LaTeX are controlled by \@listi/\@listI.
  \def\@listi{%
    \leftmargin=0pt
    \itemindent=0pt
    \labelsep=0.5em
    \labelwidth=0pt
    \listparindent=0pt
    \parsep=0pt
   % \topsep=0pt
   % \partopsep=0pt
   % \itemsep=0pt
    }%
    \let\@listI\@listi
  }

  \makeatother%

}


\newcommand{\preparesolution}[0]{
  \grading{}{Cap}
  \setbool{showbuttons}{false}
  \setbool{entermatrikel}{false}
  \setbool{showsummation}{false}
\commonsettings
}


\newcommand{\preparecorrection}[0]{%
  \commonsettings%
  \input{../../../../js/inject.js}    % inject some library functions 
  \input{../../../../js/correct.js}   % inject some more specific application functions

}% end preparecorrection



% Generate make correction from given serial number
\newcommand{\makecorrection}[1]{%
  \examSerial{#1}
  \includepdf[
    pages=-,
    width=\HalfPW,
    height=\paperheight,
    keepaspectratio,
    offset={\dimexpr-\QuarterPW-1.8cm\relax\space 0pt},
    pagecommand={\LRPageOverlay}
  ]{klausuren/\my@exam@id/pdf-exams-clean/#1.pdf}
  \setcounter{page}{1}
}


% Command describing how we overlay the included PDF with additional information
% This is called by the \includepdf command and provides the additional info
\newcommand{\LRPageOverlay}{%
  \begin{tikzpicture}[remember picture,overlay]%  Everything is under control of a tikzpicture environment
    % On the left side we have the original PDF of the exam, which we overlay with a positioning node
    \node[anchor=south west] at (current page.south west) {%
      \begin{minipage}[t][\paperheight]{\HalfPW}
        \begin{Form}
          % Input the file which typesets the form elements for the individual points obtainable in every task
          \IfFileExists{build/\my@filename.crd}{\input{build/\my@filename.crd}}{\errmessage{Fatal error: required file 'build/\my@filename.crd' not found}}     
          \footerform%                      Typesets an overview footer with PDF information and UI on every page
        \end{Form}
      \end{minipage}%
    };
    \node[anchor=north east] at (current page.north east) {SERIAL
      \TextField[name=Serial,width=2.5cm,height=0.6cm,borderwidth=1,charsize=12pt,readonly=true,bordercolor={0 0 0},value={\myexamserial}]{}
    };
    % Input the file which typesets the right side of the page, using the solution information which was dumped to .sol
    \IfFileExists{build/\my@filename.sol}{\input{build/\my@filename.sol}}{\errmessage{Fatal error: required file 'build/\my@filename.sol' not found}}     
  \end{tikzpicture}%
}




% Generate a sample solution / grading scheme only for the correctors
\newcommand{\makesolution}{

  \examSerial{1}%
  \includepdf[
    pages=-,
    width=\HalfPW,
    height=\paperheight,
    keepaspectratio,
    offset={\dimexpr-\QuarterPW-1.8cm\relax\space 0pt},
    pagecommand={\LRPageOverlaySolution}
  ]{../../../../klausuren/\my@exam@id/tex/build/\my@exam@id.pdf}
  \setcounter{page}{1}
}


\newcommand{\LRPageOverlaySolution}{%
  \begin{tikzpicture}[remember picture,overlay]%  Everything is under control of a tikzpicture environment
    % On the left side we have the original PDF of the exam, which we overlay with a positioning node
    \node[anchor=south west] at (current page.south west) {%
      \begin{minipage}[t][\paperheight]{\HalfPW}
        \begin{Form}%
          % Input the file which typesets the form elements for the individual points obtainable in every task
%%          \IfFileExists{build/\my@filename.crd}{\input{build/\my@filename.crd}}{\errmessage{Fatal error: required file 'build/\my@filename.crd' not found}}     
          \footerform%                      Typesets an overview footer with PDF information and UI on every page
        \end{Form}%
      \end{minipage}%
    };
    \node[anchor=north east] at (current page.north east) {SERIAL
      \TextField[name=Serial,width=2.5cm,height=0.6cm,borderwidth=1,charsize=12pt,readonly=true,bordercolor={0 0 0},value={\myexamserial}]{}
    };
    % Input the file which typesets the right side of the page, using the solution information which was dumped to .sol
    \IfFileExists{build/\my@filename.sol}{\input{build/\my@filename.sol}}{\errmessage{Fatal error: required file 'build/\my@filename.sol' not found}}     
  \end{tikzpicture}%
}




\makeatother
%END_FOLD







%
%BEGIN_FOLD  Hooks
%

\AtBeginDocument{
  \IfFileExists{build/\jobname.tot}{\input{build/\jobname.tot}}{}
}


% File into which we write the total number of points
\AtEndDocument{
  \newwrite\totalfile
  \immediate\openout\totalfile=\jobname.tot
  \immediate\write\totalfile{\string\setcounter{totalpointsfromfile}{\number\value{totalpoints}}}
  \immediate\closeout\totalfile
}
%END_FOLD



\endinput