# Changelog

Formatet följer Keep a Changelog, och versionsnumren följer semantisk versionering.

## [1.0.0] - 2026-10-19
Kommentarer, README och testprotokoll för Delrapport 2. Koden är fryst och taggad v1.0.0.
- 0.10.1: README.md och docstrings: provat i en ren klon
- v0.10.2: underlaget till frysen: kravmatrisen, A01 och betataggen
- v1.0.0: frysen: koden från v0.10.2beta oförändrad, Adrians tester och testprotokoll till och med Testa 0.9 (pytest grön), Issue #7 väg B (facit_07 efter koden). Inte gjort före taggen: A11, A13, A06, A15, A07, Uppgift 16 och frysmappen.

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

