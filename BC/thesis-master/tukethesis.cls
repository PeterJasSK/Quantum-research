%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%r
%%
%% TUKE Thesis Class.
%%
%% Class for writing bachelor/master/phd thesis
%% at Technical University of Košice.
%%
%% project homepage: https://git.kpi.fei.tuke.sk/tuke/thesis.in.latex
%%
%%%%%
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{tukethesis}[2025/09/19 TUKE Thesis Class, v2025.4]


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Class options
%%
%% Class is based on the report class, so it accepts all of it's options.
%% Additional options are for the main and other languages of the thesis.
%%
%% Example usage:
%%
%%     \documentclass[mainlanguage=english,otherlanguage=slovak]{tukethesis}
%%
%%%%%

\RequirePackage{kvoptions}
\RequirePackage{xstring}

% definition of class options
\SetupKeyvalOptions{
  family=tukethesis,
  prefix=tukethesis@
}

% set default options
\DeclareStringOption[slovak]{mainlanguage}
\DeclareStringOption[english]{otherlanguage}

% process keyval options
\ProcessKeyvalOptions*

% validation: mainlanguage ≠ otherlanguage
\IfStrEq{\tukethesis@mainlanguage}{\tukethesis@otherlanguage}{%
  \ClassError{tukethesis}
    {mainlanguage and otherlanguage must be different}
    {You set both languages to '\tukethesis@mainlanguage', but they must be different.}
}{}

% use report class as base.
\PassOptionsToClass{a4paper,12pt,oneside}{report}
\LoadClass{report}

% set language options
\RequirePackage{polyglossia}
\setmainlanguage{\tukethesis@mainlanguage}
\setotherlanguage{\tukethesis@otherlanguage}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Additional packages, and their options.
%%
%%%%%

\RequirePackage{nameref}      %% named references
\RequirePackage{pdfpages}

% titlesec for modification of chapters and sections
\RequirePackage{titlesec}
\titleformat{\chapter}
    {\huge\bfseries}                        % font
    {\thechapter}                           % numbering
    {20pt}                                  % spacing
    {\huge\bfseries}[{\titlerule[0.8pt]}]   % label

% sets the document geometry
\RequirePackage[
    a4paper,
    %width=150mm,
    top=25mm,
    bottom=25mm,
    left=30mm,
    right=25mm,
    bindingoffset=6mm
]{geometry}

\RequirePackage{graphicx}
\DeclareGraphicsExtensions{.pdf,.png,.jpg,.eps}

%% for printing source code
% See for details: https://en.wikibooks.org/wiki/LaTeX/Source_Code_Listings
% GitHub colors (https://gist.github.com/maelquerre/b625bda6cab11c1b0ae67a2be86f027e)
% \definecolor{GitHubBlue}{HTML}{005CC5}
% \definecolor{GitHubDarkBlue}{HTML}{032F62}
% \definecolor{GitHubGray}{HTML}{6A737D}
% \definecolor{GitHubGreen}{HTML}{22863A}
% \definecolor{GitHubOrange}{HTML}{E36209}
% \definecolor{GitHubPurple}{HTML}{6F42C1}
% \definecolor{GitHubRed}{HTML}{D73A49}

% \colorlet{Keyword}{GitHubRed}
% \colorlet{Function}{GitHubBlue}
% \colorlet{Method}{GitHubPurple}
% \colorlet{String}{GitHubDarkBlue}
% \colorlet{Comment}{GitHubGray}

\RequirePackage{listings}
\lstdefinestyle{default}{
   basicstyle=\small\ttfamily,  % smaller typewriter font
   showstringspaces=false,      % don't show spaces in string
   captionpos=t,                % place caption above listings
   % commentstyle=\color{GitHubGray},
   % keywordstyle=\color{GitHubRed},
   % stringstyle=\color{GitHubDarkBlue}
}
\lstset{style=default}


%% for professional-looking tables
\usepackage{booktabs}



%% Numeric citations and sorting by citation order
\RequirePackage{csquotes}
\RequirePackage[
    bibencoding=auto,
    style=iso-numeric,      % numeric citations according for ISO 690
    autolang=other,
    sorting=none,           % sort by order of citation
    backend=biber           % different backend
]{biblatex}

% slovak translation of bibliography
\DefineBibliographyStrings{slovak}{%
    bibliography = {Zoznam použitej literatúry}
}
% \def\bibname{Zoznam použitej literatúry} % TODO replaced by biblatex stuff, should be \bibname either

\RequirePackage[
   unicode,
   %backref,
   pdfusetitle,
   %pdfusekeywords,
   pdftoolbar=true,
   pdfmenubar=true,
   pdfwindowui=true,
   pdfproducer={TUKE Thesis v2025.4},
   pdfcreator={XeLaTeX},
   bookmarksopenlevel={0},
   bookmarksnumbered,
   bookmarksopen,
   pdfhighlight={/P},
   colorlinks=true,
   %hidelinks, % disable color links completly
   citecolor=magenta,
   linkcolor=magenta,
   filecolor=magenta,
   urlcolor=magenta,
%    baseurl={https://kpi.fei.tuke.sk/}
]{hyperref}


% popisky ku obrazkom a tabulkam
\RequirePackage[small]{caption}
\setlength{\captionmargin}{25pt}

%% Vlastná hlavička
\RequirePackage{fancyhdr}
\setlength{\headheight}{15pt}

% nastavenie hlavičky pre hlavnú časť práce
\pagestyle{fancy}
\renewcommand{\chaptermark}[1]{
    \markboth{\ifnum\value{chapter}>0 \chaptername\ \thechapter.\ \fi #1}{}
}
\fancyhf{}
\rhead{\itshape \nouppercase{\leftmark}}
\rfoot{\thepage}


% štýl pre prvú stranu kapitoly (plain s číslom strany v päte zarovnaný vpravo)
\fancypagestyle{chapterpage}{
    \fancyhf{}
    \renewcommand\headrulewidth{0pt}
    \rfoot{\thepage}
}


% zmena štýlu prvej stránky kapitoly
\renewcommand\chapter{
    \if@openright\cleardoublepage\else\clearpage\fi
    \thispagestyle{chapterpage}
    \global\@topnum\z@
    \@afterindentfalse
    \secdef\@chapter\@schapter
}

\renewcommand{\headrulewidth}{0.7pt}


% slovnik terminov a skratiek
\RequirePackage[
    toc,
    acronym,
    nonumberlist,
    noredefwarn
]{glossaries}
\loadglsentries{glossary}
\makeglossaries % prikaz na vytvorenie suboru .glo


% good linebraking of bibtex url
\setcounter{biburllcpenalty}{7000}
\setcounter{biburlucpenalty}{8000}
\setcounter{biburlnumpenalty}{7000}


% continue footnote numbering over pages and chapters
\counterwithout{footnote}{chapter}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Variable definitions and default values: these variables should be defined by
%% the user (somewhere in the preamble). For example, to put the abstract into
%% the thesis, the thesis writer should type the following somewhere in the
%% preamble (before the `\begin{document}` or `\frontmatter` commands are
%% called):
%%
%%      \abstract{This is my abstract.}
%%
%% See below (in the comments starting with 'DOCVAR: ') for a list of all variables
%% the thesis writer is expected to use.
%%
%%%%%

%\def\br{\\}

% DOCVAR: thesisspec (The list of thesis specifications)
\newcommand{\@thesisspec}{
    \thispagestyle{empty}
    \vspace*{\fill}
    \begin{center}
        \iflanguage{slovak}{

            \noindent
            \makebox[\linewidth]{%
                \parbox{\linewidth}{%
                    Na túto stranu vložte zadávací list. To urobíte nasledovne:

                    \begin{enumerate}
                        \item Zadávací list naskenujte v odtieňoch sivej (čiernobielo) na $200$ až $300$ DPI.
                        \item Sken uložte do priečinku \texttt{figures/}.
                        \item V súbore \texttt{metadata.tex} zadajte umiestnenie súboru pomocou príkazu {\texttt{\textbackslash{}thesisspec\{figures/zadavaci.list\}}}
                    \end{enumerate}

                    {\bf Do jednej kópie práce však nezabudnite vložiť originál zadávacieho listu!}
                }%
            }
        }{}
        \iflanguage{english}{
            Here insert the assignment statement using the command\\
            {\tt{\textbackslash{}thesisspec\{path/to/the/filw/with/assignment.statement\}}}\\
            in the preamble of the document.

            Copy of the assignment statement should be scanned black\&white (grayscale) using DPI from $200$ to $300$!
            Don't forget to insert the original assignment statement into one of the theses copies.
        }{}
    \end{center}
    \vspace*{\fill}
    \newpage
}
\newcommand{\thesisspec}[1]{
    \renewcommand{\@thesisspec}{
        \includepdf[pages={-}]{#1}
    }
}


% Command for author's name in the form of: [affil]{Name}{Surname}[affil]
% Second optional argument using https://texfaq.org/FAQ-twooptarg
\newcommand{\@author@prefix}{}
\newcommand{\@author@firstname}{}
\newcommand{\@author@lastname}{}
\newcommand{\@author@postfix}{}
\renewcommand\author[3][]{
    \renewcommand{\@author@prefix}{#1}
    \renewcommand{\@author@firstname}{#2}
    \renewcommand{\@author@lastname}{#3}
    \authorpostfix
}
\newcommand\authorpostfix[1][]{
    \renewcommand{\@author@postfix}{#1}
}


% DOCVAR: college (The name of the thesis writer's college)
\newcommand{\@college@en}{Technical University of Košice}
\newcommand{\@college@sk}{Technická univerzita v Košiciach}
\newcommand{\@college}{\@college@en}
\newcommand{\college}[2]{
    \renewcommand{\@college@en}{#1}
    \renewcommand{\@college@sk}{#2}
}

\newcommand{\@college@city}{Košice}

% DOCVAR: faculty (The name of the thesis writer's faculty)
\newcommand{\@faculty@en}{Faculty of Electrical Engineering and Informatics}
\newcommand{\@faculty@sk}{Fakulta elektrotechniky a informatiky}
\newcommand{\@faculty}{\@faculty@en}
\newcommand{\faculty}[2]{
    \renewcommand{\@faculty@en}{#1}
    \renewcommand{\@faculty@sk}{#2}
}


% DOCVAR: department (name of the thesis writer's department)
\newcommand{\@department@en}{Department of Computers and Informatics}
\newcommand{\@department@sk}{Katedra počítačov a informatiky}
\newcommand{\@department}{\@department@en}
\newcommand{\department}[2]{
    \renewcommand{\@department@en}{#1}
    \renewcommand{\@department@sk}{#2}
}


% DOCVAR: department's shortcut
\newcommand{\@departmentacr@en}{DCI}
\newcommand{\@departmentacr@sk}{KPI}
\newcommand{\@departmentacr}{\@departmentacr@en}
\newcommand{\departmentacr}[2]{
    \renewcommand{\@departmentacr@en}{#1}
    \renewcommand{\@departmentacr@sk}{#2}
}


% DOCVAR: supervisor (name of the thesis writer's supervisor)
\newcommand{\@supervisor}{}
\newcommand{\supervisor}[1]{\renewcommand{\@supervisor}{#1}}

% DOCVAR: consultant (name of the thesis writer's consultant)
\newcommand{\@consultant}{}
\newcommand{\consultant}[1]{\renewcommand{\@consultant}{#1}}

% DOCVAR: consultant's workplace
\newcommand{\@consultantsaffiliation@en}{}
\newcommand{\@consultantsaffiliation@sk}{}
\newcommand{\@consultantsaffiliation}{\@consultantsaffiliation@en}
\newcommand{\consultantsaffiliation}[2]{
    \renewcommand{\@consultantsaffiliation@en}{#1}
    \renewcommand{\@consultantsaffiliation@sk}{#2}
}

% DOCVAR: field of study
\newcommand{\@fieldofstudy}{Informatika}
\newcommand{\fieldofstudy}[1]{\renewcommand{\@fieldofstudy}{#1}}

% DOCVAR: study programme
\newcommand{\@studyprogramme}{Informatika}
\newcommand{\studyprogramme}[1]{\renewcommand{\@studyprogramme}{#1}}

% DOCVAR: thesis (type of the thesis)
\newcommand{\@thesis@en}{Bachelor thesis}
\newcommand{\@thesis@sk}{Bakalárska práca}
\newcommand{\@thesis}{\@thesis@en}
\newcommand{\thesis}[2]{
    \renewcommand{\@thesis@en}{#1}
    \renewcommand{\@thesis@sk}{#2}
}

% DOCVAR: declaration text
\newcommand{\@declaration@en}{I hereby declare that this thesis is my own work and effort. Where other sources of information have been used, they have been acknowledged.}
\newcommand{\@declaration@sk}{Vyhlasujem, že som záverečnú prácu vypracoval samostatne s~použitím uvedenej odbornej literatúry.}
\newcommand{\@declaration}{\@declaration@en}
\newcommand{\declaration}[1]{
    \renewcommand{\@declaration@en}{#1}
    \renewcommand{\@declaration@sk}{#1}
}

% DOCVAR: date (declaration date)
\newcommand{\@submissiondate}{}
\newcommand{\submissiondate}[3]{
    \newcommand{\@submissionday}{#1}
    \newcommand{\@submissionmonth}{#2}
    \newcommand{\@submissionyear}{#3}
}

% DOCVAR: abstract of the thesis
\renewcommand{\abstract}[2]{%
    \newcommand{\@abstract@en}{#1}%
    \newcommand{\@abstract@sk}{#2}%
}
\newcommand{\@abstract}{\@abstract@en}

% DOCVAR: thesis keywords
\newcommand{\keywords}[2]{%
    \newcommand{\@keywords@en}{#1}%
    \newcommand{\@keywords@sk}{#2}%
}
\newcommand{\@keywords}{\@keywords@en}

% DOCVAR: thesis title
\renewcommand{\title}[2]{%
    \newcommand{\@title@en}{#1}%
    \newcommand{\@title@sk}{#2}%
}
\renewcommand{\@title}{\@title@en}


% DOCVAR: thesis (type of the thesis)
\newcommand{\@acknowledgment}{%
    Na tomto mieste by som sa rád poďakoval svojmu vedúcemu záverečnej práce za pripomienky a~odbornú pomoc.
}
\newcommand{\acknowledgment}[1]{\renewcommand{\@acknowledgment}{#1}}


% right page number aligment from 2nd page in table of content
\fancypagestyle{plain}{%
    \renewcommand{\footrulewidth}{0pt}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Front matter
%%
%% - outside and inside front cover
%% - title leaf
%% Do not include the date of make!
%% Institution + department.
%% Names of referees. (optional)
%% Degree.
%% Date of submission and defense. (optional)
%% Place and date of publication and publishers (and other info by them).
%%
%%%%%

\newcommand{\frontmatter}{
    \pagenumbering{roman}
    \pagestyle{empty}  % no page numbers until TOC
    \frontpage
    \titlepage
    \abstractpage

    % thesis detail specification
    \@thesisspec

    \declarationpage
    \acknowledgmentpage

    \pagestyle{plain}
    \tableofcontents
    \newpage

    % show list of figures only if there are some
    \iftotalfigures%
        \listoffigures%
        \newpage%
    \fi

    % show list of tables only if there are some
    \iftotaltables%
        \listoftables%
        \newpage%
    \fi

    % show list of listings only if there are some
    \iftotallstlistings%
        \lstlistoflistings%
        \newpage%
    \fi

    \pagestyle{fancy}
    \pagenumbering{arabic}
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Back matter
%%
%%%%%
\newcommand{\backmatter}{
    %% The bibliography
    \printbibliography[heading=bibintoc]

    \label{theend} % the last page of the thesis

    % List of acronyms
    \printglossary[type=\acronymtype,title={\acrlistname}]

    % Glossaries
    \printglossary
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Front page component
%%
%%%%%
\newcommand{\frontpage}{
    \def\br{\\}

    \begin{center}
        {\Large \textbf{\@college}}

        {\Large \textbf{\@faculty}}

        \vfill

        {\LARGE \textbf{\@title} \par}

        \bigskip

        {\large \textbf{\@thesis}}
    \end{center}

    \vfill

    \begin{center}
        {\Large \textbf{\@submissionyear}} \hfill {\Large \textbf{\@author@prefix~\@author@firstname~\@author@lastname~\@author@postfix}}
    \end{center}

    \newpage
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Abstract component
%%
%%%%%
\newcommand{\abstractpage}{
    \def\br{}

    \noindent
    \subsection*{\abstractname}

    \@abstract

    \subsection*{\keywordsname}

    \@keywords

    \iflanguage{slovak}{
        \subsection*{\secondabstractname}

        \begin{otherlanguage}{english}
            \@abstract
        \end{otherlanguage}

        \subsection*{\secondkeywordsname}

        \begin{otherlanguage}{english}
            \@keywords
        \end{otherlanguage}
    }{
        \subsection*{\secondabstractname}

        \begin{otherlanguage}{slovak}
            \@abstract
        \end{otherlanguage}

        \subsection*{\secondkeywordsname}

        \begin{otherlanguage}{slovak}
            \@keywords
        \end{otherlanguage}
    }

    \vfill

    \subsection*{\bibcitationname}

    \MakeUppercase\@author@lastname, \@author@firstname. {\itshape \@title}. \@college@city: \@college, \@faculty, \@submissionyear. \pageref{theend}~\pageabbr{} \supervisorcitationname: \@supervisor

    \newpage

    \def\br{\\}
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Declaration component
%%
%%%%%
\newcommand\declarationpage{
    \vglue0pt
    \vfill
    \subsection*{\declarationname}

    \noindent\@declaration

    \bigskip

    \noindent \@college@city,~\@submissionday.\@submissionmonth.\@submissionyear \hfill
    \begin{tabular}[t]{c}
        \hbox to 50mm {\dotfill} \\ \textit{\small \signaturename}
    \end{tabular}
    \newpage
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Declaration component
%%
%%%%%
\newcommand\acknowledgmentpage{%
    \vglue0pt\vfill%

    \subsection*{\acknowledgementname}%

    \@acknowledgment

    \newpage
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Title page component
%%
%%%%%
\renewcommand{\titlepage}{
    \begin{center}
        {\Large \textbf{\@college}}

        {\Large \textbf{\@faculty}}

        \vfill

        {\LARGE \textbf{\@title} \par}

        \bigskip

        {\large \textbf{\@thesis}}
    \end{center}

    \vfill

    \noindent
    \begin{tabular}{@{}p{.32\textwidth}p{.7\textwidth}}
        \studyprogrammename:& \@studyprogramme \\
        \fieldofstudyname:& \@fieldofstudy \\
        \supervisorname:& \@supervisor \\
        \departmentname:& \@department~(\@departmentacr) \\
        \if\@consultant\empty\else\consultantname:& \@consultant \\ \fi
        \if\@consultantsaffiliation\empty\else\consultantsaffiliationname:& \@consultantsaffiliation \\ \fi
    \end{tabular}

    \vspace{2\baselineskip}

    \begin{center}
        \centering
        {\Large \textbf{\@college@city{} \@submissionyear}} \hfill {\Large \textbf{\@author@prefix~\@author@firstname~\@author@lastname~\@author@postfix}}
    \end{center}

    \newpage
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Font Settings
%%
%%%%%

% Set the fonts
\RequirePackage{fontspec}
\setmainfont{TeX Gyre Pagella}   % \rmfamily{}
\setsansfont{TeX Gyre Heros}[Scale=MatchLowercase]   % \rmfamily{}
\setmonofont[
    Path = fonts/,
    Extension = .otf,
    UprightFont = *-Regular,
    BoldFont = *-Bold,
    ItalicFont = *-It,
    BoldItalicFont = *-BoldIt,
    Scale=MatchLowercase
]{SourceCodePro}   % \ttfamily{}

% Set math font
\RequirePackage{unicode-math}
\setmathfont{TeX Gyre Pagella Math}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Line spacing and paragraph indentation
%%
%%%%%

\linespread{1.3}
\setlength{\parindent}{1.5em}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Translations of strings used in the thesis
%%
%%%%%

% Default empty declarations
\newcommand{\declarationname}{No Language Selected}
\newcommand{\signaturename}{No Language Selected}
\newcommand{\acknowledgementname}{No Language Selected}
\renewcommand{\lstlistingname}{No Language Selected}
\newcommand{\studyprogrammename}{No Language Selected}
\newcommand{\fieldofstudyname}{No Language Selected}
\newcommand{\departmentname}{No Language Selected}
\newcommand{\supervisorname}{No Language Selected}
\newcommand{\consultantname}{No Language Selected}
\newcommand{\consultantsaffiliationname}{No Language Selected}
\newcommand{\keywordsname}{No Language Selected}
\newcommand{\secondabstractname}{No Language Selected}
\newcommand{\secondkeywordsname}{No Language Selected}
\newcommand{\bibcitationname}{No Language Selected}
\newcommand{\supervisorcitationname}{No Language Selected}
\newcommand{\acrlistname}{No Language Selected}
\newcommand{\appendixlistname}{No Language Selected}
\newcommand{\pageabbr}{No Language Selected}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\AtBeginDocument{
    \addto\captionsenglish{
        \renewcommand{\@abstract}{\@abstract@en}
        \renewcommand{\@college}{\@college@en}
        \renewcommand{\@consultantsaffiliation}{\@consultantsaffiliation@en}
        \renewcommand{\@declaration}{\@declaration@en}
        \renewcommand{\@department}{\@department@en}
        \renewcommand{\@departmentacr}{\@departmentacr@en}
        \renewcommand{\@faculty}{\@faculty@en}
        \renewcommand{\@keywords}{\@keywords@en}
        \renewcommand{\@thesis}{\@thesis@en}
        \renewcommand{\@title}{\@title@en}
        \renewcommand{\abstractname}{Abstract in English}
        \renewcommand{\acknowledgementname}{Acknowledgement}
        \renewcommand{\acrlistname}{List of Abbreviations}
        \renewcommand{\appendixlistname}{List of Appendices}
        \renewcommand{\bibcitationname}{Bibliographic Citation}
        \renewcommand{\consultantname}{Consultant}
        \renewcommand{\consultantsaffiliationname}{Consultant's Affiliation}
        \renewcommand{\declarationname}{Declaration}
        \renewcommand{\departmentname}{Supervising Department}
        \renewcommand{\fieldofstudyname}{Field of Study}
        \renewcommand{\figurename}{Figure}
        \renewcommand{\keywordsname}{Keywords in English}
        \renewcommand{\lstlistingname}{Listing}
        \renewcommand{\lstlistlistingname}{List of \lstlistingname s}
        \renewcommand{\pageabbr}{p.}
        \renewcommand{\signaturename}{Signature}
        \renewcommand{\studyprogrammename}{Study Programme}
        \renewcommand{\supervisorname}{Supervisor}
        \renewcommand{\secondabstractname}{Abstract in Slovak}
        \renewcommand{\secondkeywordsname}{Keywords in Slovak}
        \renewcommand{\supervisorcitationname}{Supervisor}
    }
    \addto\captionsslovak{
        \renewcommand{\@abstract}{\@abstract@sk}
        \renewcommand{\@college}{\@college@sk}
        \renewcommand{\@consultantsaffiliation}{\@consultantsaffiliation@sk}
        \renewcommand{\@declaration}{\@declaration@sk}
        \renewcommand{\@department}{\@department@sk}
        \renewcommand{\@departmentacr}{\@departmentacr@sk}
        \renewcommand{\@faculty}{\@faculty@sk}
        \renewcommand{\@keywords}{\@keywords@sk}
        \renewcommand{\@thesis}{\@thesis@sk}
        \renewcommand{\@title}{\@title@sk}
        \renewcommand{\abstractname}{Abstrakt v slovenčine}
        \renewcommand{\acknowledgementname}{Poďakovanie}
        \renewcommand{\acrlistname}{Zoznam skratiek}
        \renewcommand{\appendixlistname}{Zoznam príloh}
        \renewcommand{\appendixname}{Príloha}
        \renewcommand{\appendixautorefname}{Príloha}
        \renewcommand{\bibcitationname}{Bibliografická citácia}
        \renewcommand{\consultantname}{Konzultant}
        \renewcommand{\consultantsaffiliationname}{Pracovisko konzultanta}
        \renewcommand{\declarationname}{Čestné vyhlásenie}
        \renewcommand{\departmentname}{Školiace pracovisko}
        \renewcommand{\fieldofstudyname}{Študijný odbor}
        \renewcommand{\figurename}{Obrázok}
        \renewcommand{\glossaryname}{Slovník termínov}
        \renewcommand{\keywordsname}{Kľúčové slová v slovenčine}
        \renewcommand{\lstlistingname}{Výpis}
        \renewcommand{\lstlistlistingname}{Zoznam výpisov}
        \renewcommand{\pageabbr}{s.}
        \renewcommand{\secondabstractname}{Abstrakt v angličtine}
        \renewcommand{\secondkeywordsname}{Kľúčové slová v angličtine}
        \renewcommand{\signaturename}{Vlastnoručný podpis}
        \renewcommand{\studyprogrammename}{Študijný program}
        \renewcommand{\supervisorname}{Školiteľ}
        \renewcommand{\supervisorcitationname}{Vedúci práce}
    }

    % Disable color links in the final version (define \printable in metadata.tex)
    \ifdefined\printable
        \hypersetup{hidelinks}
    \fi
}

% Polyglossia sets the language only in \AfterEndPreambule
\AfterEndPreamble{
    % PDF metadata based on macro values and current language
    \def\br{}
    \iflanguage{english}{
        \hypersetup{
            pdftitle = {\@title@en},
            pdfauthor = {\@author@firstname~\@author@lastname},
            pdfkeywords = {\@keywords@en},
            pdfsubject = {\@thesis@en}
        }
    }{
        \hypersetup{
            pdftitle = {\@title@sk},
            pdfauthor = {\@author@firstname~\@author@lastname},
            pdfkeywords = {\@keywords@sk},
            pdfsubject = {\@thesis@sk}
        }
    }
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\makeatletter

% redefine \chapter command to remove vertical space in lof and lot
\def\@chapter[#1]#2{%
    \ifnum \c@secnumdepth >\m@ne
        \refstepcounter{chapter}%
        \typeout{\@chapapp\space\thechapter.}%
        \addcontentsline{toc}{chapter}{\protect\numberline{\thechapter}#1}%
    \else
        \addcontentsline{toc}{chapter}{#1}%
    \fi
    \chaptermark{#1}%
    \def\@currentlabelname{#2}%
    % \addtocontents{lof}{\protect\addvspace{10\p@}}%
    % \addtocontents{lot}{\protect\addvspace{10\p@}}%
    \if@twocolumn
        \@topnewpage[\@makechapterhead{#2}]%
    \else
        \@makechapterhead{#2}%
        \@afterheading
    \fi
}

% list of figures without indentation
\renewcommand*{\l@figure}[2]{%
  \@dottedtocline{1}{0em}{2.5em}{#1}{#2}%
}

% list of tables without indentation
\renewcommand*{\l@table}[2]{%
  \@dottedtocline{1}{0em}{2.5em}{#1}{#2}%
}

% list of listings without indentation
\renewcommand*{\l@lstlisting}[2]{%
  \@dottedtocline{1}{0em}{2.5em}{#1}{#2}%
}

\makeatother


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Appendix style
%%
%%%%%

\newcommand{\setappendixstyle}{
   % no entries from appendixes in the table of contents
   \renewcommand{\addcontentsline}[3]{}

   % change the chapter numbering to appendixes
   \titleformat{\chapter}
        {\huge\bfseries}                        % font
        {\thechapter}                           % numbering
        {20pt}                                  % spacing
        {\huge\bfseries}[{\titlerule[0.8pt]}]   % label

   % use arabic numbers for sections, figures, tables, and listings
   \renewcommand{\thesection}{\arabic{section}}
   \renewcommand{\thefigure}{\arabic{figure}}
   \renewcommand{\thetable}{\arabic{table}}
   \renewcommand{\thelstlisting}{\arabic{lstlisting}}
}


%% total counters for conditional showing of lists
% must be defined after all packages with required counters
\RequirePackage[
    figure,
    table,
    lstlisting
]{totalcount}
