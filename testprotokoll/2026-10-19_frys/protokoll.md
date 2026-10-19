# Frysprotokoll: frysrundan på v1.0.0

Datum: 2026-10-19. Dator: DESKTOP-NFJKKB3 (Windows, PowerShell 5.1.26100.9711). Python: Python 3.12.10.
Commit: 1770adb 1.0.0: frysen. Issue #7 vag B: facit_07 efter koden; CHANGELOG 1.0.0; protokollet. Tagg: v1.0.0. pytest: 32 passed (PASSED 64 gånger i pytest.txt, -v -rA). ruff: All checks passed!.
Testare och miljö, ur testprotokoll/protokoll.md:
- Testare: Adrian Lindstedt
- Dator: SAMSUNG ELECTRONICS CO., LTD. Galaxy Book4 Edge
- Operativsystem: Microsoft Windows 11 Home (ARM 64-bitarsprocessor)
- Python: Python 3.12.15 (x64, körs emulerat på ARM)
- Rundan 2026-10-19 kväll (A11, Testa 0.7 och 0.8b, A13, A06, A15, A07, Uppgift 16, A16, Slutkoll och denna frysrunda): körd av Elias Holmberg på DESKTOP-NFJKKB3 (Windows x64), Adrian frånvarande.

Testerna visar att räkningarna stämmer med sina tal. De visar inte att instrumentet mäter rätt: kamerans tal är relativa, aldrig watt eller verkningsgrad.

## DR2-tabellen

| Fall | Vad | Krav | Vem | Uppgift | Tagg | Datum | Status | Kommentar |
|---|---|---|---|---|---|---|---|---|
| A01 | ren installation | 9 | Elias | 0.10.1 | v0.10.2beta (klon av 37b03fb) | 2026-10-19 | Godkänt | A01 (Krav 9), ren installation, gjord av Elias (till-adrian.md 2026-10-19 06:40): ren klon av 37b03fb den 2026-10-19 på Windows DESKTOP-NFJKKB3 (PowerShell 5.1), README följd rad för rad (Windows-listan steg 3-10), check_install.py: Installationen stämmer., pytest -k elias 16 passed, klon-pytest.txt: 19 passed in 0.56s, exempelkörningen gav Topp 200 vid våglängd (nm) 412 (1 bild). Godkänt. Rättat i README: inget. Ny klon av v1.0.0 från GitHub 2026-10-19 kväll: check_install OK, ruff grön, pytest 32 passed. |
| A02 | första körningen | 10 | Adrian | Uppgift 6 (steg 8) | v0.3.3beta2 | 2026-10-19 | Godkänt | terminal.txt (överskriven 03:10) och fonster.png gjorda om med alla tre körningar; gamla: terminal-transkript-0310.txt, fonster-20261018.png; mätmapp 20261019-052918 även i A17, raw.png kontrollrad rätt |
| A17 | CSV i kalkylprogram | 12 | Adrian | Uppgift 6 (steg 8) | v0.3.3beta | 2026-10-19 | Godkänt | steg.md |
| A11 | prompten | 10 | Elias | Uppgift 7 (steg 15) | v1.0.0 | 2026-10-19 | Godkänt | automatiserad av Elias, inte för hand: samma kommandon som för hand matade till det riktiga main.main() av A11\a11_prov.txt, Ctrl+C under step och vid prompten simulerat med _thread.interrupt_main och KeyboardInterrupt, Ctrl+Z som EOFError; source file först (ingen kamera); help 16 rader, roi utan höjd, channel purple och foo ger Fel: utan traceback, roi oförändrad efter felet (T17), show 14 rader, Avbrutet. och prompten igen, tyst avslut vid Ctrl+Z och Ctrl+C; tangenterna själva bevisas också av test_elias.py; A11\terminal.txt |
| A03 | spara en mätning (T09 och A17) | 12 | Adrian | Uppgift 8 (struken) | - | 2026-10-19 | Struket | Uppgift 8 är Bra att ha och struken (Elias 2026-10-19); spara-kedjan bevisas av test_csv, A17 och Testa 0.5 |
| A13 | live och avslut | 13 | Elias | Uppgift 9 (steg 16a) | v1.0.0 | 2026-10-19 | Blockerat | live med kameran: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; utan kamera bevisat med bildfil och camera 99 (Testa 0.6) och test_elias.py |
| A06 | kalibrering | 16 | Elias | Uppgift 11 (steg 16b) | v1.0.0 | 2026-10-19 | Blockerat | kalibrering mot Hg-linjer: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; räkningen bevisad av test_rx09_eval, test_fit_rx10, test_load_points och Testa 0.7 |
| A15 | respons | 14 | Elias | Uppgift 12 (steg 16c) | v1.0.0 | 2026-10-19 | Blockerat | respons mot känd lampa: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; kedjan bevisad av test_rx03, test_rx16, test_response_rx14/rx15, test_load_known_rx14, Testa 0.8 och Uppgift 16 |
| A07 | transmission | 15 | Elias | Uppgift 13 (steg 16d) | v1.0.0 | 2026-10-19 | Blockerat | transmission med färgfilter: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; kedjan bevisad av test_rx17, Testa 0.9 och Uppgift 16 |
| A16 | kodbilagan | 11 | Elias | Uppgift 15 (steg 18) | v1.0.0 | 2026-10-19 | Godkänt | docstrings: 62 def i 7 filer, ingen saknas, ruff --select D1 grön; kod.pdf inte kontrollerad (finns inte än); git diff --stat v0.10.2beta v1.0.0 -- spectrometer tom; körd av Elias |
| A05, A09 | medel över flera bilder | 10 | Adrian | Testa 0.5 och frysrundan (steg 14 och 17), frames 5 och 30 med bildfil | v0.10.2beta | 2026-10-19 | Godkänt | frames 5 och 30 med bildfil: Topp 200 vid pixel 12 (5 bilder) och (30 bilder), ingen varning; Testa\a05_a09.txt; i frysrundan 2026-10-19 igen (Elias): A05_A09/terminal.txt |

Strukna fall, med förenklingen i README som orsak:

- T10 och pausdelen av A04: programmet har inga tillstånd
- T13: programmet har inga trådar
- läsdelen av T09: mätmappen läses inte tillbaka
- speccore-delen av A01: det finns ingen core.py
- Uppgift 8 (A03, RX07), Uppgift 10 och tests/valfria.py: Bra att ha, strukna i en-runda-planen (Elias 2026-10-19)

## Rundorna och testfunktionerna

Raderna ur testprotokoll/protokoll.md med taggen v0.10.2beta (Adrians runda) och v1.0.0 (Elias runda), samma kod i spectrometer/:

| ID | krav | tagg | datum | status | kommentar |
|---|---|---|---|---|---|
| Förberedelse | - | v0.10.2beta | 2026-10-19 | Godkänt | merge 49f96d3, check_install OK, pytest 22 passed, ruff grön |
| RX06 | Krav 10 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx06 i tests/test_calc.py (b51d96f): medel 3, 10, 6 och spridning med N - 1 (RX06), N = 1 ger NaN utan varning (RX07); kopia med fel facit röd |
| RX09-RX10 + load_points | Krav 16 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx09_eval och test_fit_rx10 i tests/test_calc.py, test_load_points i tests/test_files.py (fel rubrik, fel antal fält, check inte 0/1), t04.csv; pytest 26 passed |
| RX09 RX10 load_points | Krav 16 | v0.10.2beta | 2026-10-19 | Godkänt | samma som raden RX09-RX10 + load_points (8d0ca1b), med ID:t som sidan v3 använder |
| RX03 RX14 RX15 RX16 load_known | Krav 14 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx03, test_rx16, test_response_rx14, test_response_rx15 i tests/test_calc.py, test_load_known_rx14 i tests/test_files.py, rx14_t16.csv; pytest 31 passed |
| RX17 | Krav 15 | v0.10.2beta | 2026-10-19 | Godkänt | test_rx17 i tests/test_calc.py: 25/50 = 0.5, negativt prov -2/40 = -0.05 står kvar (T05), 60/50 = 1.2, referens 0.8 och exakt 1.0 ogiltiga (T06); pytest 32 passed |
| Testa 0.4 | Krav 10 | v0.10.2beta | 2026-10-19 | Godkänt | testa_04 42 rader, 3 Fel: utan traceback, roi oförändrad efter fel (T17), show 14 rader; facit_04 omsparad (help 16 rader, show 14); tom indata slutkod 0; Testa\testa_04.txt |
| Testa 0.5 | Krav 10, 12 | v0.10.2beta | 2026-10-19 | Godkänt | testa_05 lika facit_05 (15 rader), två mätmappar, settings.json frames 3; Testa\testa_05.txt |
| Testa 0.6 | Krav 13 | v0.10.2beta | 2026-10-19 | Godkänt | start på bildfil: fönster, live stoppad vid krysset; source camera 99 och start: Fel camera.open_failed utan traceback; Testa\testa_06_fonster.txt |
| Testa 0.7 | Krav 16 | v0.10.2beta | 2026-10-19 | Godkänt | testa_07 lika facit_07 (25 rader: a0 400, a1 1, Topp 200 vid våglängd (nm) 412, kontrollfel 1.5 med varning, 0.4 utan, semikolon.csv fel rubrik); fönstrets x-axel 410 till 414 enligt Adrian: ja; Testa\testa_07.txt |
| Testa 0.8 | Krav 14 | v0.10.2beta | 2026-10-19 | Godkänt | testa_08a (11 rader) och testa_08b (35 rader) lika facit: mörker medel 10 med varning, Topp 0 efter mörker, respons 3 av 3, Topp 400 vid 515 med respons, responsen glömd vid roi; Testa\testa_08a.txt, testa_08b.txt |
| Testa 0.9 | Krav 15 | v0.10.2beta | 2026-10-19 | Godkänt | testa_09 lika facit_09 (46 rader: Topp 1 och Topp 0.5 i transmission, fel vid annan roi och kanal än referensens, referensen glöms vid dark), spectrum.csv med absorbance, settings.json mode transmission; Testa\testa_09.txt |
| A05, A09 | Krav 10 | v0.10.2beta | 2026-10-19 | Godkänt | frames 5 och 30 med bildfil: Topp 200 vid pixel 12 (5 bilder) och (30 bilder), ingen varning; Testa\a05_a09.txt |
| Testa 0.7 rättad | Krav 16 | v0.10.2beta | 2026-10-19 | Underkänt | Issue #7: calibrate semikolon.csv ger fel rubrik, väntade pixel,wavelength_nm,check; guiden v45 och facit_07 ger fel rubrik ['pixel;wavelength_nm;check']; övriga rader lika facit_07; raden Testa 0.7 (Godkänt) var fel; Testa\testa_07.txt |
| Testa 0.8 rättad | Krav 14 | v0.10.2beta | 2026-10-19 | Godkänt | testa_08b ger respons 2 av 3, inte 3 av 3: pixel 10 blir 499.99999999999994 nm, under den kända filens 500 nm (avrundning i numpy på den här datorn; NaN utanför enligt RX15, inte fel i koden); facit_08b omsparad (2c268e9); testa_08a och 08b lika facit; raden Testa 0.8 sade 3 av 3; Testa\testa_08a.txt, testa_08b.txt |
| A11 | Krav 10 | v1.0.0 | 2026-10-19 | Godkänt | automatiserad av Elias, inte för hand: samma kommandon som för hand matade till det riktiga main.main() av A11\a11_prov.txt, Ctrl+C under step och vid prompten simulerat med _thread.interrupt_main och KeyboardInterrupt, Ctrl+Z som EOFError; source file först (ingen kamera); help 16 rader, roi utan höjd, channel purple och foo ger Fel: utan traceback, roi oförändrad efter felet (T17), show 14 rader, Avbrutet. och prompten igen, tyst avslut vid Ctrl+Z och Ctrl+C; tangenterna själva bevisas också av test_elias.py; A11\terminal.txt |
| Testa 0.7 rättad 2 | Krav 16 | v1.0.0 | 2026-10-19 | Godkänt | Issue #7 väg B (Elias): facit_07 rad 24 följer koden; testa_07 lika facit_07 (25 rader) på v1.0.0, körd av Elias på Windows x64; Testa\testa_07_v1.0.0.txt |
| Testa 0.8 rättad 2 | Krav 14 | v1.0.0 | 2026-10-19 | Godkänt | testa_08b lika facit_08b (35 rader, respons 3 av 3) på v1.0.0, körd av Elias på Windows x64; testdatan rättad (ingen kodändring): x12_kand.csv har en extra punkt vid 490 nm så att pixel 10 (500 nm, på vissa datorer 499.99999999999994 nm) ligger inne i den kända fördelningen, och facit_08b är som från början; samma svar på x64 och ARM; Testa\testa_08b_v1.0.0.txt |
| A13 | Krav 13 | v1.0.0 | 2026-10-19 | Blockerat | live med kameran: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; utan kamera bevisat med bildfil och camera 99 (Testa 0.6) och test_elias.py |
| A06 | Krav 16 | v1.0.0 | 2026-10-19 | Blockerat | kalibrering mot Hg-linjer: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; räkningen bevisad av test_rx09_eval, test_fit_rx10, test_load_points och Testa 0.7 |
| A15 | Krav 14 | v1.0.0 | 2026-10-19 | Blockerat | respons mot känd lampa: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; kedjan bevisad av test_rx03, test_rx16, test_response_rx14/rx15, test_load_known_rx14, Testa 0.8 och Uppgift 16 |
| A07 | Krav 15 | v1.0.0 | 2026-10-19 | Blockerat | transmission med färgfilter: uppställningen (kamera, lysrör, lampa, filter) saknas 2026-10-19; görs i efterhand före DR2 om den kommer; raden skriven av Elias; kedjan bevisad av test_rx17, Testa 0.9 och Uppgift 16 |
| Uppgift 16 | Krav 14, 15 | v1.0.0 | 2026-10-19 | Godkänt | mörker, respons och transmission med testbilder (RX19, RX14): mörker medel 2 ger 11, 30, 52; respons 3 av 3 ger 52 vid 500-502 nm; transmission 0.5 vid 500 och 501 nm, lucka vid 502; körd av Elias på Windows x64; utskrift16.txt, Uppgift16\ (tre mätmappar), testfiler\rx19_* |
| A16 | Krav 11 | v1.0.0 | 2026-10-19 | Godkänt | docstrings: 62 def i 7 filer, ingen saknas, ruff --select D1 grön; kod.pdf inte kontrollerad (finns inte än); git diff --stat v0.10.2beta v1.0.0 -- spectrometer tom; körd av Elias |
| Slutkoll | Krav 9-16 | v1.0.0 | 2026-10-19 | Godkänt | pytest 32 passed, ruff grön, taggar: v1.0.0 v0.10.2beta v0.9.3beta2 v0.8.3beta2 v0.7.3beta v0.6.2beta; körd av Elias |

## Mappar i frysmappen

- A01/
- A02/
- A05_A09/
- A11/
- A17/
- Testa/
- Uppgift16/
- pytest.txt, protokoll.md, kravmatris.md
