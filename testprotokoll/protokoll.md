# Testprotokoll – spektrometern

- Testare: Adrian Lindstedt
- Dator: SAMSUNG ELECTRONICS CO., LTD. Galaxy Book4 Edge
- Operativsystem: Microsoft Windows 11 Home (ARM 64-bitarsprocessor)
- Python: Python 3.12.15 (x64, körs emulerat på ARM)

| ID | krav | tagg | datum | status | kommentar |
|-------|---------|------|----------|-------|-----------|
| A01 | Krav 9 | v0.3.3beta | 2026-10-18 | Godkänt | Installation fungerar på Windows ARM med x64-Python. pytest: 1 failed (test_csv), se Issue. |
| testkort | Krav 10 | - | 2026-10-18 | Godkänt | RX01, RX02 och RX05 i testkort, stämmer med Testkartan |
| Issue #2 | - | v0.3.3beta2 | 2026-10-18 | Godkänt | pytest 3 passed, ruff utan fel. Issue stängd. |
| A02 | Krav 10 | v0.3.3beta2 | 2026-10-18 | Godkänt | Topp 200 vid pixel 12, slutkod 0; finns_inte.png ger camera.open_failed och 1. fonster.png, terminal.txt |
| A17 | Krav 12 | v0.3.3beta2 | 2026-10-18 | Godkänt | spectrum.csv i Excel: tal i egna kolumner, inga datum. raw.png kontrollrad rätt. Mätmapp 20261018-223713, steg.md |
| testfiler | - | - | 2026-10-19 | Godkänt | Issue #3: rand_x12.png, t04.csv och rx14_t16.csv (LF-radslut) |
| test_calc | Krav 10 | v0.3.3beta2 | 2026-10-19 | Godkänt | tests/test_calc.py: 3 passed, ruff grön. Skickad i Issue #4, inte committad |
| protokoll | - | - | 2026-10-19 | Godkänt | Fyra rader och tabell; [prov] Uppgift 2 #5 stängd; [adrian] Besked #6 fäst |
| testfiler | - | v0.3.3beta | 2026-10-19 | Godkänt | rand_x12.png lika |
| RX01 RX02 RX05 | Krav 10 | v0.3.3beta | 2026-10-19 | Godkänt | testkort, test_calc.py |
| Testa 0.1 | Krav 10 | v0.3.3beta | 2026-10-19 | Godkänt | |
| Testa 0.2 | Krav 10 | v0.3.3beta | 2026-10-19 | Godkänt | testa02_fonster.png |
| Testa 0.3 | Krav 10, 12 | v0.3.3beta | 2026-10-19 | Godkänt | |
| A02 | Krav 10 | v0.3.3beta | 2026-10-19 | Godkänt | fonster.png, terminal.txt |
| A17 | Krav 12 | v0.3.3beta | 2026-10-19 | Godkänt | steg.md |
| rad 18-24 rättad | - | v0.3.3beta2 | 2026-10-19 | - | Rad 18-24 har fel tagg v0.3.3beta (skrivna 03:38 med en annan AI, inte kontrollerade) och gäller inte. Steg 6-8 görs om på v0.3.3beta2 och får nya rader. |
| Testa 0.1 | Krav 10 | v0.3.3beta2 | 2026-10-19 | Godkänt | 5 kanaler rätt (sum kontrollerad med python -c, Testa01\sum-prov2.txt: TEMP-körningen gav 30 för sum p.g.a. gammal .pyc, blockets fel, inte koden), __main__ bara i main.py, pytest 6 passed, rött-provet 1 failed 5 passed, ruff grön; Testa01\utskrift.txt |
| Testa 0.2 | Krav 10 | v0.3.3beta2 | 2026-10-19 | Godkänt | 20 tal, 200. på plats 12, en kurva efter bytet (1), stängt utan traceback, pytest 6 passed in 0.54s, ruff grön; testa02_fonster.png (efter bytet), Testa02\terminal.txt |
| Testa 0.3 | Krav 10, 12 | v0.3.3beta2 | 2026-10-19 | Godkänt | pytest 6 passed, ruff grön; rand_x12.png: Topp 200 vid pixel 12, slutkod 0, mappen raw.png settings.json spectrum.csv, 12,200,true; finns_inte.png: camera.open_failed, slutkod 1; utan sökväg: usage, slutkod 2; A02\terminal.txt |
| A02 rättad | Krav 10 | v0.3.3beta2 | 2026-10-19 | Godkänt | terminal.txt (överskriven 03:10) och fonster.png gjorda om med alla tre körningar; gamla: terminal-transkript-0310.txt, fonster-20261018.png; mätmapp 20261019-052918 även i A17, raw.png kontrollrad rätt |
| testfiler | - | v0.3.3beta2 | 2026-10-19 | Godkänt | rand_x12.png lika: (10, 20, 3) uint8 6000 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 200, 0, 0, 0, 0, 0, 0, 0] |
| RX01 RX02 RX05 | Krav 10 | v0.3.3beta2 | 2026-10-19 | Godkänt | testkort RX01.md RX02.md RX05.md, test_calc.py: 3 passed in 0.14s |
| tester | - | v0.3.3beta2 | 2026-10-19 | Godkänt | grenen tester, verktyg.ps1 (sidans text), tests/test_calc.py, pytest 6 passed, ruff grön |
| Förberedelse | - | v0.10.2beta | 2026-10-19 | Godkänt | merge 49f96d3, check_install OK, pytest 22 passed, ruff grön |
| RX06 | Krav 10 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx06 i tests/test_calc.py (b51d96f): medel 3, 10, 6 och spridning med N - 1 (RX06), N = 1 ger NaN utan varning (RX07); kopia med fel facit röd |
| RX09-RX10 + load_points | Krav 16 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx09_eval och test_fit_rx10 i tests/test_calc.py, test_load_points i tests/test_files.py (fel rubrik, fel antal fält, check inte 0/1), t04.csv; pytest 26 passed |
