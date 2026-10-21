# Changelog

Formatet följer Keep a Changelog, och versionsnumren följer semantisk versionering.

## [1.2.16] - 2026-10-20

### Tillagt
- `figure UT.png --cie [MAPP...]`: kromaticitetsdiagram med hästskon, Planck-kurvan och en punkt per mätning.
- `demo/mät.txt` skriver rapportfiguren (`figure data/figur.png`).
- Analyspanelerna `view analysis colour|rgb|droop|edge|performance` visar det `color`, `mix`, `series plot`, `bandgap` och `perf` senast räknade (förut: otillgängligt).

## [1.2.15] - 2026-10-20

### Ändrat
- FWHM räknas över en rak baslinje mellan toppens baspunkter (rev7) och är ogiltig för en mättad topp, vid kanten och när en topp intill har dalen över halva höjden.
- Färgtemperaturen är närmaste punkten på svartkroppskurvan i CIE 1960 uv, med Duv; ingen CCT när |Duv| är över 0,01 (rev7). McCamy står inom parentes.

### Tillagt
- `bandgap --anpassa`: två räta linjer med brytpunkt (rev7), minst åtta punkter, 3-standardfelsregeln och ändpunktskontroll. Standard är fortfarande brantaste lutningen.

## [1.2.14] - 2026-10-20

### Tillagt
- `spectrum.csv`: kolumnen `stddev` efter `raw_counts`, spridningen mellan bilderna (tom vid en bild).
- `out.pm`: `värde ± osäkerhet` med 1–2 värdesiffror i osäkerheten (RAP-14) i `bandgap`, `fwhm` (med minst två bilder) och `series plot` (upprepade mätningar vid samma ström).
- `dark save FIL.npy` och `dark load FIL.npy` med formkontroll.

## [1.2.13] - 2026-10-20

### Rättat
- `bandgap`: ingen kant (Fel-rad) när absorbansen stiger mindre än 0,1 från låg till hög energi; brus kring T ≈ 1 gav förut ett värde.
- `calibrate save` utan uppmätt upplösning sparar som förut men varnar (`resolution_nm` blir null).
- `load`, `compare`, `figure`, `mix` och `bandgap` på en mapp som inte är en mätmapp: en Fel-rad i stället för `[Errno 2]`.
- `mix` varnar inte för olika roi när en mätning har `roi full` och ytan är densamma.
- `__version__` följer utgåvan igen (stod på 1.0.32).

## [Unreleased]
- Startskärm: `py -m spektro` (Windows) eller `python3 -m spektro` (Linux) bygger `.venv` vid behov och startar programmet med prisma och gul text (`--windowed`, `--no-splash`, `--delay SEK`). Färgerna är ANSI-koder, inget nytt bibliotek i requirements.txt. Konsten ligger i `startskarm/prisma.py`, utanför `spectrometer/`; koden i `spectrometer/` är oförändrad sedan v1.0.0.

## [1.0.32] - 2026-10-20

- Utgåvorna 1.0.1-1.2.12 enligt planen (PowerShell-skripten spektro-*.ps1).

## [1.0.0] - 2026-10-19
Kommentarer, README och testprotokoll för Delrapport 2. Koden är fryst och taggad v1.0.0.
- 0.10.1: README.md och docstrings: provat i en ren klon
- v0.10.2: underlaget till frysen: kravmatrisen, A01 och betataggen
- v1.0.0: frysen: koden från v0.10.2beta oförändrad, Adrians tester och testprotokoll till och med Testa 0.9 (pytest grön), Issue #7 väg B (facit_07 efter koden). Inte gjort före taggen: A11, A13, A06, A15, A07, Uppgift 16 och frysmappen.
- Efter taggen, 2026-10-19 (grenen adrianfemboygaming, koden i spectrometer/ och taggen v1.0.0 oförändrade): A11 Godkänt (automatiserad), Testa 0.7 och 0.8b rättade (ny testdata tests/kommandon/x12_kand.csv), A13, A06, A15 och A07 Blockerat (uppställningen saknas), Uppgift 16, A16 med kod.pdf (Krav 11), slutkollen och frysmappen testprotokoll/2026-10-19_frys. Kvar: kamerabeviset (Krav 13) på uppställningen.

## [0.9] - 2026-10-19
Lagt till transmission (reference [N] och mode direct|transmission). Kommandon som ändrar mätningen tömmer den gamla.
- 0.9.1: calc.py: transmissionskvoten
- 0.9.2: main.py: reference och mode
- v0.9.3: main.py: transmission i measure, show, step och save

## [0.8] - 2026-10-19
Lagt till mörkerkorrigering (dark [N]) och responskorrigering (response build KNOWNFILE, response on och response off).
- 0.8.1: main.py: dark och avdraget i measure
- 0.8.2: calc.py: responsen räknas
- v0.8.3: main.py: response och korrigerad signal

## [0.7] - 2026-10-19
Lagt till våglängdskalibrering: kommandot calibrate PATH [DEGREE], läsning av punktfiler och x-axel i nm.
- 0.7.1: calc.py: evaluate_wavelength och fit_wavelength
- 0.7.2: files.py: load_points läser punktfilen
- v0.7.3: main.py: calibrate och x-axeln i nm

## [0.6] - 2026-10-19 - Lagt till webbkameran som källa (V4L2 på Linux, DirectShow på Windows) och kommandot start, som visar spektrumet live tills Ctrl+C eller tills fönstret stängs. measure kan låna en öppen källa, och kameran släpps alltid (T15).

- 0.6.1 source.py: kameran som källa, Linux och Windows. open_source, read_frame och close_source har kameragrenar med camera.open_failed och camera.read_failed. README.md har ## Kamera, med låsta reglage och exponering.
- 0.6.2 main.py: measure lånar källan och start visar live. Betatagg v0.6.2beta för 0.4-0.6.

## [0.5] - 2026-10-19 - Lagt till medelvärde över flera bilder: average_spectra i calc.py och kommandona frames, step och save i main.py (Krav 12). step skriver toppen och varnar när råbilden är mättad.

- 0.5.1 calc.py: average_spectra ger medel och spridning av flera spektrum, en rad per bild.
- 0.5.2 main.py: frames, step och save. measure tar medel av frames bilder, och save sparar senaste mätningen i en ny mätmapp.

## [0.4] - 2026-10-19 - Lagt till kommandoraden: en prompt med help, quit, show, source, roi, channel och axis. Ett fel skrivs som en rad och prompten fortsätter (T17).

- 0.4.1 main.py: hjälpfunktionerna AXES, _to_int, _need och _set, och kommandona help, quit och show.
- 0.4.2 main.py: kommandona source, roi, channel och axis, och ordboken COMMANDS med alla sju.
- 0.4.3 main.py: prompten fungerar. run_command delar en rad och anropar rätt kommando, och main läser rader tills quit eller Ctrl+D.

## [0.0] - 2026-10-16 - Lagt till projektmappen: paketet spectrometer med __init__.py och fem tomma programfiler, tests/, pyproject.toml, requirements-filerna, README.md och CHANGELOG.md.

- 0.0.1 Program på datorn: git, uv, github-cli, base-devel, psmisc, v4l-utils och guvcview med pacman, och VS Code med tilläggen Python, Pylance och Ruff.
- 0.0.2 Repot på datorn: inloggning med gh, git-identiteten, klonen av repot och grenen adrianfemboygaming.
- 0.0.3 Python 3.12 och miljön: `.python-version` och `.venv/`. Första commiten.
- 0.0.4 Biblioteken och pyproject.toml: numpy, opencv-python, matplotlib, pytest och ruff, `requirements.txt`, `requirements-dev.txt` och `pyproject.toml`.
- 0.0.5 Paketet och mappen tests: `spectrometer/` med `__init__.py` och fem tomma programfiler, och `tests/.gitkeep`.
- 0.0.6 .gitignore och README: `.gitignore` och `README.md` med Installation.
- 0.0.7 CHANGELOG.md: den här filen.
- 0.0.8 Kontroll av projektmappen: pytest och ruff körda, tagg v0.0.8. Rättat i efterhand i 0.0.8-2 (pyproject.toml, tests/.gitkeep, .gitignore, tom main.py) och 0.0.8-3 (pyproject.toml på rätt plats, README, CHANGELOG, todo.txt ur git).

