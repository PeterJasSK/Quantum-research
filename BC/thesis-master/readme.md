# About

Template for final theses writing at _Technical University of Košice_.

Warning! The encoding of all documents is set to _UTF-8_! So don't forget to set up your environment in which you will write your thesis to use this encoding!

## Structure


* [thesis.tex](thesis.tex) is the main file of the thesis. Use it to include additional chapters or appendices and to use any additional LaTeX packages or macros.
* [metadata.tex](metadata.tex) contains the title of the thesis, author's name, and all other metadata.
* [bibliography.bib](bibliography.bib) with the bibliography entries.
* [chapters/](./chapters/) contains files with the main parts of your thesis. You should add more as needed.
* [appendices/](./appendices/) contains appendices, manuals, and other supplementary materials.
  * [appendices/00-list.tex](appendices/00-list.tex) is a list of appendices.
* [glossary.tex](glossary.tex) is a list of terms and their descriptions.
* [acronyms.tex](acronyms.tex) contains acronyms and their meanings.


## Build with Docker

For building your thesis you can also use [Docker image](https://hub.docker.com/repository/docker/kpituke/latex/general)

```bash
$ docker container run --rm -it \
    --volume .:/data \
    --user $(id --user):$(id --group) \
    kpituke/latex \
    make pdf
```

If you are using Linux OS or WSL, you can use prepared shell script, which is located in this repository, by typing:

```bash
$ ./mkthesis.sh
```

The basic workflow for writing can be used with following targets:

```bash
$ ./mkthesis.sh clean watch
```

Your thesis will be watched for changes. If there will be any change, your PDF file will be recompiled automatically. Resulting PDF file will be located in the `dist/` directory.

Alternatively, you can create an alias in your shell configuration file (e.g. `~/.bashrc` or `~/.zshrc`):

```bash
$ alias mkthesis='docker container run --rm -it \
    --volume .:/data \
    --user $(id --user):$(id --group) \
    --name thesis \
    kpituke/latex \
    make '
```

Then you can run your build simply with command:

```bash
$ mkthesis 
```


## Install Locally

If you want to install LaTeX locally, we recommend using the [TeX Live](https://www.tug.org/texlive/) package.

Fedora users will write:

```bash
$ sudo dnf install \
    texlive-collection-latexrecommended \
    texlive-collection-fontsrecommended \
    texlive-collection-langczechslovak \
    texlive-biblatex-iso690 \
    texlive-totalcount \
    texlive-glossaries \
    latexmk
```

Similarly, Debian and Ubuntu users will write:

```bash
$ sudo apt-get install --yes \
   texlive-latex-extra \
   texlive-fonts-recommended \
   texlive-lang-czechslovak \
   texlive-bibtex-extra \
   biber \
   latexmk
```


## Compilation

The template expect that you would use modern versions of LaTeX: **XeLaTeX** or **LuaLaTeX**. XeLaTeX is configured by default in `.latexmkrc`, so to create a document, type the following command from the command line:

```bash
$ latexmk -pvc thesis
```

Running this command will create the resulting document in _PDF_ format, which will be displayed in the document browser afterwards. However, the tool will not quit and will monitor changes, while with each change (saving a _.tex_ file), the resulting document will be re-generated.

Of course, you can open the project in any _LaTeX_ editor or IDE, e.g. _TeX Studio_.

## Editors for Writing Your Thesis in LaTeX

There exists many _LaTeX_ editors and extensions for common code editors for _LaTeX_ support. You can try these:

* [TeXstudio](https://www.texstudio.org/) – _TeXstudio_ is an IDE for creating _LaTeX_ documents.
* [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop) – _VS Code_ extension for writing _LaTeX_ documents (use `latexmk (xelatex)` recipe for building).
* [vimtex](https://github.com/lervag/vimtex) – a modern Vim and neovim filetype plugin for LaTeX files


## Update

In case the template is updated, just update the `tukethesis.cls` file in your project. However, always look in the `changelog.md` file to make sure there was an update.


## Spell Checking

In case your editor does not support spell-checking, you can use the `aspell` tool as follows:

```bash
aspell -d sk_SK -t -c file.tex
```

For VS Code we recommend [Spell Right](https://marketplace.visualstudio.com/items?itemName=ban.spellright) extension.


## Troubleshooting

### Q1: I found an error in the template. Where can I report it?

Either by e-mail to miroslav.binas@tuke.sk or directly here on gitlab. Ideally with a _merge request_.


### Q2: The page numbering of the table of contents is in Roman numerals. Is that all right?

Yes, it is OK. The work uses two styles of page numbering. Numbering with Roman numerals is in the introductory part of the work (table of contents and all lists). Numbering of the rest of the work, starting from the introduction or motivation, is numbered in Arabic numerals. Numbering of the second part of the work begins on the page with the introduction or motivation.


### Q3: Table of contents is not displayed.

Try compiling the work again. It is typical for _LaTeX_. If you want to have your table of contents updated, it is always necessary to translate it twice.


### Q4: The bibliography only shows 3 records, even though I have more.

_BibTeX_ is used to generate the bibliography. It only displays those items that you actually quote in the work. Therefore, if you cite only 3 documents in the work, only those will be displayed in the bibliography.


## Additional Resources

### LaTeX writing support for popular IDEs and editors

* [TeXiFy IDEA for IntelliJ IDEs](https://plugins.jetbrains.com/plugin/9473-texify-idea)
* [LaTeX Workshop for VS Code](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
* [VimTeX: A modern Vim and neovim filetype plugin for LaTeX files](https://github.com/lervag/vimtex)


### Books about using LaTeX

* [The Not So Short Introduction to LaTeX 2ε](https://tobi.oetiker.ch/lshort/lshort.pdf) (recommended)
* [Nie príliš stručný úvod do systému LaTeX 2ε](http://mirrors.ctan.org/info/lshort/slovak/Slshorte.pdf) (Slovak translation of older version)
* [LaTeX Wikibook](https://en.wikibooks.org/wiki/LaTeX)
