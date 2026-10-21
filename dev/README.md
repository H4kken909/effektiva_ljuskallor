# dev/: det som bara utvecklingen behöver

Programmet, testerna och CI behöver inget härifrån. Allt i den här mappen kan tas bort utan att programmet ändras.

| Vad | Innehåll |
|---|---|
| `check.py` | Kör allt: ruff, pytest (tempmapp utanför projektet), import av paketet, jämförelse mot baslinjen. `.venv/Scripts/python.exe dev/check.py`, med `--rot MAPP` för en annan utcheckning. Loggar i `check-logg/` (git-ignorerad). |
| `inventera.py` | Listar varje fil med storlek, radantal, sha256, typ och git-status. |
| `baslinje/` | `GRANSSNITT.md` (frysta gränssnitt), `kommandon.json` och `utdata/` (sparade utskrifter som check jämför mot). `--spara-baslinje` skriver om dem. |
| `verktyg-elias.ps1`, `verktyg-elias.sh`, `PROTOKOLL-ELIAS.md` | Elias protokollverktyg och logg från testrundorna. Flyttade hit orörda; de antar att de ligger i repots rot och fungerar inte härifrån. |
| `verktyg/` | `kopiera-data` (mätdata till USB) och `las` (kamerans reglage), för riggen. |
| (`patchskript/`) | De tre `spektro-*.ps1` som byggde 1.0.15–1.2.12 låg här efter fas 3 men togs bort i fas 4 (Elias 13A); de finns i `git show rensning/fas3-klar:dev/patchskript/<fil>` och i bundlen. |
| `testprotokoll/` | Adrians manuella testprotokoll, facit och frysmappen för Delrapport 2. |
| `README-gammal.md` | Den gamla, långa README:n (600 rader) som den var vid 1.2.16. |

## Grenarna main och dev

- `main` är programmet utan `dev/`. Ändringar i programmet görs på `main`.
- `dev` är en exakt kopia av `main` plus `dev/`. Efter varje ändring på `main` slås `main` ihop in i `dev`
  (alltid från main till dev). Ändringar i `dev/` görs bara på `dev`. `dev` slås aldrig ihop in i `main`.
