# Change Log

All notable changes to this project will be documented in this file.

## [2025.4] - 2025-09-19
- Návrat k použitiu XeLaTeX namiesto luaTeX (je rýchlejší)
- Znovu pridanie fontov SourceCodePro (jednoduchšia inštalácia aj bez Dockeru)
- Presunutie štýlov a tried naspäť do koreňového adresára, takže nie je nutné meniť premenné prostredia
- Pridané pracovisko konzultanta v metadátach
- Zlepšenia .latexmkrc
- Zostavovanie rozdielových PDF pomocou git-latexdiff v CI


## [2025.3] - 2025-06-10
- do triedy `tukethesis` boli pridané dve možnosti pre jazyk:
  - `mainlanguage` - pre hlavný jazyk práce
  - `otherlanguage` - pre druhý jazyk práce
  - predvolene je hlavný jazyk slovenčina a druhý jazyk je angličtina


## [2025.2] - 2025-06-05
- priecinok `appendixes/` bol premenovany na `appendices/`
- navrat ku prekladu pomocou _LuaLaTeX_
  - refaktoring `Makefile` suboru v Docker obraze 
  - aktualizacia aj konfiguracneho suboru `.latexmkrc`
- refaktoring pravidiel v `Makefile`
  - aktualne sa `latexmk` pouziva aj na preklad veci, kde sa zapina `\printable`
  - cely cas bol problem s escapovanim lomitok :-)
- overenie, ci je preklad v rezime `printable` sa presunul do sablony
  - priznak `\printable` bol presunuty do metadat spolu s komentarom ako a preco a kedy ho pouzivat
- text cestneho vyhlasenia v metadatach je zakomentovany a je v zenskom rode
  - text v sablone je v muzskom rode
  - student si podla toho upravi/pouzije ten, ktory mu vyhovuje a nebude tam ziadne _vypracoval(a)_
- do sablony pridana podpora pre balik `luavlna`
  - v Docker obraze sa instaluje prislusny balik `texlive-luavlna`
- pridaný preklad `\glossaryname` na `Slovník termínov`
  - pôvodne bol len `Slovník`
  - preklad je podľa _Katuščáka_, alternatívou môže byť `Slovník pojmov`
- skratky AJ a SJ pri abstrakte a klucovych slovach boli prepisane na _angličtina_ a _slovenčina_
- pocet strán v bibliografickej citácii
  - pridaná medzera medzi počtom strán a skratkou (zrejme aj podľa štandardu ISO 690, https://ippr.sk/c/204-citacie-parafrazy-bibliograficke-odkazy-iso-690)
  - pridaný anglický a slovenský preklad


## [2025.1] - 2025-06-03
- v projekte prace vytvoreny samostatny priecinok `texmf/`, do ktoreho bola presunuta sablona, a v ktorom sa mozu nachadzat dalsie lokalne veci
- odstraneny priecinok `fonts/`
    - fonty su dostupne ako samostatny balik a boli doinstalovane do docker obrazu
    - zo sablony vyhodena informacia o ich umiestneni na disku
- aktualizovana/opravena dokumentacia
- `dist` priecinok bol nastaveny ako vystupny v konfiguracii `.latexmkrc`
    - vystupny dokument sa zostavi v priecinku `dist/` a nie v lokalnom priecinku
- obsah obrázkov, tabuliek a výpisov
    - bola odstránená vertikálna medzera oddeľujúca položky z rozličných kapitol
    - bola odstranena aj horizontalna medzera, ktorá odsadzovala položky viac vpravo (keďže sa položky číslujú s prefixom kapitoly, do ktorej patria)
    - nezobrazujú sa ani prázdne obsahy, ak sa obrázky, tabuľky a výpisy nachádzajú len v prílohách
- z obsahu boli vyhodené prílohy a ich obsah
- podkapitoly príloh je možné číslovať:
    - bez prefixu prílohy, alebo
    - vôbec (potlačením číslovania pomocou znaku `*`)
- osobitná príloha _LaTeX 101_ so základmi LaTeX-u


## [2024.9] - 2024-09-26
- Replace LuaLaTeX with XeLaTeX (it is faster).
- Replace babel with polyglossia.
- Set Source Code Pro as a monospace font and bundle the font files.
- Improve `.latexmkrc` configuration.
- Disable colorful syntax highlighting of listings.
- Move `Makefile` and _Docker_ configuration to [kpi/latex](https://git.kpi.fei.tuke.sk/kpi/latex) project.
- Move example thesis text to [kpi/thesis.example](https://git.kpi.fei.tuke.sk/kpi/thesis.example) project.


## [2024.3] - 2024-07-08
- pridanie ďalšieho príkazu `shell` do súboru `Makefile` (thesis maker)
   - spustí shell pre surový prístup do kontajnera so zdrojovými súbormi práce
- prechod od `pdflatex`-u do `lualatex`-u
   - refaktoring šablóny
   - refaktoring súboru `Makefile`
- pribudlo pravidlo `fonts` do súboru `Makefile` pre zobrazenie dostupných fontov
   - pravdepodobne je to dočasné, ale možno by nebolo zlé spraviť niečo ako "Testovací dokument", kde by boli všetky možnosti/štýly/fonty toho, ako to v dokumente vyzerá
   - a možno by to mohla byť špeciálna príloha
- `vlna` nahradená za balík `luavlna`
- do Docker obrazu bol pridaný skript `mkthesis.sh`
   - len pre použitie vo vnútri spusteného kontajnera


## [2024.2] - 2024-06-23
- na zostavovanie práce vytvorený samostatný Docker obraz
- do Docker obrazu presunutý am súbor `Makefile`, v ktorom sa nachádzajú aj ďalšie nástroje na kontrolu práce
- pridaný preklad pre prílohu pre automatické referencie v zozname príloh
- pridane dva ciele pre `Makefile`
    - `thesis` - verzia urcena pre tlac
    - `ethesis` - ebook verzia (s farebnymi linkami)
- poznamky pod ciarou pokracuju v cislovani napriek kapitolami
- pridane pravidlo `make dist` pre vytvorenie celej distribucie pre odovzdanie prace
   - `thesis-main.pdf` - len hlavna praca - verzia urcena pre tlac
   - `thesis-full.pdf` - cela praca aj s prilohami - verzia urcena pre tlac
   - `ethesis-main.pdf` - len hlavna praca - ebook verzia
   - `ethesis-full.pdf` - cela praca aj s prilohami - ebook verzia
- pri preklade vznikol priecinok `build/`, v ktorom sa nachadza vysledok prekladu so vsetkymi priebezne vytvaranymi subormi. tym padom je vysledny projekt cistejsi
- konfiguracia pre `latexmk` bola presunuta do Docker obrazu do priecinku `/app`
- v pravidle `dist` su pouzite samostatne prikazy na zostavenie vysledných dokumentov, pretože pri spustení príkazu `latexmk` vždy dôjde k chybe
- vytvorené nové makro `\printable`, pomocou ktorého je možné zapnúť/vypnúť farebné linky


## [2024.1] - 2024-04-14
- vypustené čestné vyhlásenie z práce
- pridaný súbor `Makefile` na zostavovanie práce
- prvá verzia bakalárskej práce o _Robotovi Karlovi_
- pridaný preklad pre balík `listings` ako "Výpis"
- osamostatnenie premenných pre definovanie metadát práce do samostatného súboru `metadata.tex`
- skratka obrázku "Obr." bola premenovaná na plný "Obrázok" po vzore tabuliek a výpisov
- zoznam výpisov sa zobrazuje automagicky na základe toho, či práca obsahuje aspoň jeden
- presunutie zoznamu literatúry z priečinku `chapters/` do hlavného priečinku práce
- styl `kithesis` bol premenovany na `tukethesis`
- vytvoreny prikaz `\backmatter{}`, do ktoreho bol vlozeny zoznam pouzitej literatury a zoznam skratiek
- do metadát PDF dokumentu bol korektne pridaný autor
- do metadát PDF dokumentu sa vkladá názov, kľúčové slová aj podnadpis na základe jazyka práce
- všetky linky sú momentálne fialové
- v obsahu už nie sú rámčeky, ale fialové odkazy
- pridanie názvu referencie pri prílohách pomocou balíka `\nameref{}`
- kopec refaktoringu a vyčistenie súboru `thesis.tex`


## [2022.1] - 2021-10-04
- consultant definition is now optional


## [2021.3] - 2021-09-29
- specification of the bibliography file removed from the class and added to the thesis.tex


## [2021.2] - 2021-03-23
- full support for English documents
- `readme.md` translated to English


## [2021.1] - 2021-02-08
- znovu zapnuté farebné ramčeky okolo odkazov
- pridaný súbor `latexmkrc` s konfiguráciou automatického generovania slovníkov (#10)


## [2020.1] - 2020-09-25
- zrušený analytický list a nahradený len abstraktom a kľúčovými slovami
- pozmenené rozloženie strany
- vrátené numerické označovanie literatúry
- zadávanie mena autora v tvare `\author[titul]{Meno}{Priezvisko}[titul]`
- pridaná bibliografická citácia práce na konci strany s abstraktom
- použitie balíka `listings` pre fragmenty kódu namiesto `minted`, ktorý vyžadoval inštaláciu Pythonu
- odstránený neaktualizovaná dokumentácia a šablóna prezentácie
- znovu zlúčené adresáre `dist/` a `thesis/`
- PDF súbor sa neukladá v repozitári, namiesto toho sa generuje pomocou Gitlab-CI
- použitie neproporcionálneho písma `txtt`
- odstránená závislosť na balíku `blindtext`
- zjednodušená štruktúra kapitol a doplnené informácie o ich obsahu
- vypnuté farebné ramčeky okolo odkazov


## [2018.1] - 2018-10-07
- pridaná podpora iso960
- názov kapitoly _Literatúra_ sa dostal do šablóny
- pridaná nová štruktúra práce na základe článku: https://www.scss.tcd.ie/joeran.beel/blog/2010/03/02/how-to-write-a-phd-thesis/
- vytvorený priečinok `dist/`, kde sa nachádza šablóna


## [2017.7] - 2017-12-19
- opravený problém s odkazom na _Motiváciu_ v obsahu, ktorý ukazoval na nesprávnu stranu
- pridaný zoznam termínov v súbore `glossary.tex`
- pridaný ľahký návod na použitie zoznamu skratiek a termínov priamo v súboroch `glossary.tex` a `acronyms.tex`
- refaktoring
    - výpis literatúry na jeden riadok spolu s položkou v obsahu
    - pre prílohy bol vytvorený samostatný priečinok `appendixes/`


## [2017.6] - 2017-11-22
- do konfigurácie balíka `babel` pridaná konfigurácia pre podporu písania literatúry v iných jazykoch ako slovenských
    - ilustráciou je zdroj napísaný po rusky


## [2017.5] - 2017-05-24
- v prípade, že vytvárate kapitolu bez číslovania, v záhlaví sa zobrazí len jej názov
- popisky (obrázkov, tabuliek) sú aktuálne o niečo menšie, aby boli odlíšiteľné od zvyšného textu
- pridany "magic" root komentar do suborov kapitol
- chyba v slovenskom texte (štúdijný -> študijný)
- zarovnanie cislovania stran vpravo v obsahu od 2. strany
- lepsie zalamovanie linkov v literature


## [2017.4] - 2017-04-25
- akceptovaný merge request od mateja
    - hlavičky a päty stránok sú orientované vpravo, keďže záverečná práca je tlačená jednostranne a text je na pravej strane
    - číslovanie stránok je aktuálne v päte a vždy vpravo
    - opravený problém s názvami príloh
- výška stránky sa kvôli číslovaniu zmenšila o 1cm


## [2017.3] - 2017-03-19
- zrušené zvýrazňovanie odkazov v šablóne
    - treba ešte zvážiť ich použitie možno spôsobom draft vs publisher ready verzia dokumentu


## [2017.2] - 2017-03-18
- opravený problém s číslovaním literatúry
    - v súbore `thesis.tex` došlo k prehodeniu riadkov pri umiestňovaní literatúry kvôli nesprávnej strane v obsahu. z pôvodného
    ```latex
    \printbibliography[title={Literatúra}]
    \addcontentsline{toc}{chapter}{Literatúra}
    ```
    sa stalo
    ```latex
    \phantomsection
    \addcontentsline{toc}{chapter}{Literatúra}
    \printbibliography[title={Literatúra}]
    ```

## [2017.1] - 2017-01-17
- zrušený balík `parskip`
    - pridaný `\noindent` do čestného vyhlásenia
    - zrušené odsadzovanie na titulných stranách
- oprava prostredia tabular na titulných stranách
    - na druhej strane už lícuje s okrajom
- vytvorený príkaz `\thesisspec{}` na zadanie cesty k zadaváciemu listu
    - ak nie je použitý, zobrazí sa na príslušnej stránke správa
    - ak je použitý, na príslušnom mieste sa vloží zadávací list
- zvacsena vyska hlavicky dokumentu


## [0.1.0] - 2015-10-19
### Changed
- Názov hlavného súboru bol premenovaný na `thesis.tex`, nakoľko adresuje ako diplomovú, tak aj bakalársku prácu
- Bol opravený problém so starým spôsobom použitia jazykovej verzie

### Added
- Bol pridaný súbor `README.md` so všobecnými informáciami o projekte a jeho používaní
- Bol pridaný súbor `CHANGELOG.md` s informáciami týkajúcimi sa zmien v projekte

