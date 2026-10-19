# Protokoll: Elias

Här skriver `klar` och `anteckna` (verktyg-elias.ps1 och verktyg-elias.sh) en rad direkt efter varje delkontroll, före commit, så att raden följer med i `git add`.

| Datum | Tid | Del | Vad | Resultat | Commit | Dator | Not |
|---|---|---|---|---|---|---|---|
| 2026-10-19 | 14:05 | 0.7.1 del 1 | evaluate_wavelength och fit_wavelength | OK | 3f2a1bc | Windows JAMAN-PC | |
| 2026-10-19 | 04:35 | kodfix 0.0-0.6 | calc, main, source, test_elias (16), check_install, verktyg-elias, PROTOKOLL-ELIAS, README/CHANGELOG | OK, 19 passed, ruff grön | c3ba437 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 04:43 | 0.7.1 del 1 | evaluate_wavelength och fit_wavelength | FEL (ruff, pytest) | 72e74f0 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 04:43 | 0.7.1 del 1 | evaluate_wavelength och fit_wavelength | OK | 72e74f0 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 04:44 | 0.7.2 del 1 | kalibrering/hg_linjer.csv, fem Hg-linjer | OK | cb5ca04 (+ändringar) | Windows DESKTOP-NFJKKB3 | NIST mercurytable2, luftvåglängder |
| 2026-10-19 | 05:03 | 0.7.2 del 2 | load_points | OK | eaa9a11 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:03 | 0.7.2 alla delar | files.py: load_points läser punktfilen | OK | e26fa6b | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:06 | 0.7.3 del 1 | calibrate och x-axeln i nm | OK | e26fa6b (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:07 | 0.7.3 del 2 | README B8 och CHANGELOG 0.7 | OK | e26fa6b (+ändringar) | Windows DESKTOP-NFJKKB3 | B8: högst ett pixelsteg |
| 2026-10-19 | 05:08 | 0.7.3 alla delar | main.py: calibrate och x-axeln i nm | OK | e26fa6b (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:08 | v0.7.3beta | betatagg pushad, Testa 0.7 kan börja | OK | 373f905 | Windows DESKTOP-NFJKKB3 | ls-remote visar taggen |
| 2026-10-19 | 05:11 | 0.8.1 del 4 | CAPTURE_FRAMES, measure, cmd_dark och dark i COMMANDS | FEL (ruff, pytest) | 373f905 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:12 | 0.8.1 del 5 | subtract_dark | FEL (ruff, pytest) | 373f905 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:12 | 0.8.1 del 6 | prepare godtar float64, mörkret dras av | FEL (ruff, pytest) | 373f905 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:13 | 0.8.1 alla delar | main.py: dark och avdraget i measure | FEL (ruff, pytest) | 1d79a15 | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:14 | 0.8.2 del 1 | build_response | FEL (ruff, pytest) | 1d79a15 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:14 | 0.8.2 del 2 | apply_response | FEL (ruff, pytest) | 1d79a15 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:14 | 0.8.2 alla delar | calc.py: responsen räknas | FEL (ruff, pytest) | abfa994 | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:15 | 0.8.3 del 1 | load_known | FEL (ruff, pytest) | abfa994 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:18 | 0.8.3 del 5 | response build, on och off, respons i measure | FEL (ruff, pytest) | abfa994 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:19 | 0.8.3 del 6 | CHANGELOG 0.8 | OK | abfa994 (+ändringar) | Windows DESKTOP-NFJKKB3 | ## [0.8] med en rad per bit |
| 2026-10-19 | 05:19 | 0.8.3 alla delar | main.py: response och korrigerad signal | FEL (ruff, pytest) | abfa994 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:19 | v0.8.3beta | betatagg pushad, Testa 0.8 kan börja | OK | f39b5fc | Windows DESKTOP-NFJKKB3 | ls-remote visar taggen |
| 2026-10-19 | 05:19 | v0.8.3 | riktig tagg efter Adrians Godkänt | OK | f39b5fc (+ändringar) | Windows DESKTOP-NFJKKB3 | Godkänt i till-elias.md |
| 2026-10-19 | 05:20 | 0.9.1 del 1 | transmission_ratio | FEL (ruff, pytest) | f39b5fc (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:22 | 0.9.2 del 3 | reference, mode och dark | FEL (ruff, pytest) | a16a620 (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:22 | 0.9.2 alla delar | main.py: reference och mode | FEL (ruff, pytest) | ac8d7aa | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:24 | 0.9.3 del 6 | snabbkollen för hela 0.9 | FEL (ruff, pytest) | ac8d7aa (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:24 | 0.9.3 alla delar | main.py: transmission i measure, show, step och save | FEL (ruff, pytest) | ac8d7aa (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:25 | 0.9.3 | betataggen v0.9.3beta | OK | e4851ea | Windows DESKTOP-NFJKKB3 | Testa 0.9 till Adrian |
| 2026-10-19 | 05:42 | 0.10.1 del 1 | D1 i ruff | FEL (ruff, pytest) | e4851ea (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:43 | 0.10.1 del 2 | docstrings och kommentarer | FEL (ruff, pytest) | e4851ea (+ändringar) | Windows DESKTOP-NFJKKB3 | |
| 2026-10-19 | 05:45 | 0.10.1 del 3 | README och exempel/del1.txt | FEL (ruff, pytest) | e4851ea (+ändringar) | Windows DESKTOP-NFJKKB3 | |
