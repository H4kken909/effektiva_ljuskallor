# Frysta gränssnitt (fas 1, 2026-10-21)

Det här är vad rensningen inte ändrar utan Elias ja. Bevis: `underlag/KODKARTA.md` i ingenjorsprojekt (avsnitt 2, 7)
och baslinjens sparade utskrifter i `dev/baslinje/utdata/`. Version vid frysningen: `spektro 1.2.16`.

## 1. Startsätt och flaggor

| Startsätt | Flaggor |
|---|---|
| `python -m spectrometer` / `python -m spectrometer.main [path]` | `--version`, `--kor FIL`, `--avsluta` (kräver `--kor`), `--camera N` eller `--input PATH`, `--output DIR` |
| `python spektro.py` (startaren med startskärm) | `--windowed`, `--no-splash`, `--delay SEK`; okända flaggor vidare till spectrometer.main |
| `python -m spectrometer.analys KOMMANDO MAPP` | `sammanfatta`, `toppar [--min F] [--antal N]`, `farg`, `kant` |
| `python check_install.py` | `--kamera N [--bilder K]` |
| `python tools/gen_kommandon.py [--check]`, `python tools/felkatalog.py [UT.md]` | |

Slutkoder: spectrometer.main ger 1 om något kommando gav `Fel:` och stdin inte är en terminal, annars 0; argparse 2.
`spektro-start.txt` i arbetsmappen körs före första prompten om stdin är en terminal. `SPEKTRO_DEBUG` i miljön
kastar oväntade fel vidare; annars loggas de till `logs/spektro.log`.

## 2. Kommandona vid prompten `spektro>` (70 st, i help-ordning)

help, quit, show, status, version, source, roi, channel, axis, frames, info, cameras, snap, image, step, save, start,
stability, perf, calibrate, toppar, dark, response, reference, mode, run, wait, reset, undo, history, clear, set, rows,
background, response save/load, dark save/load, rigg, theme, view, graf, roi show/auto/profile/band/move, axis detect,
exposure, gain, auto, note, series start/note/stop/plot, load, fwhm, compare, figure, color, mix, bandgap, repeat,
linearity, calibrate save, guide, pause, help limits.

Hela help-texten med argument står ordagrant i `dev/baslinje/utdata/testa_04.txt` (rad 3–71; fyra rader ändrade med
Elias ja i BESLUT 15A: image, start, theme, roi show). Beteende ändrat med samma ja: när referensen glöms i mode
transmission blir mode direct (`mode: direct (ingen referens)`, facit_09), och `clear all` tar bara mörker,
kalibrering, respons, referens, mode och senaste mätningen (BESLUT 9). Ordningen låses av
`tests/test_architecture.py` och av `FEATURES` i `spectrometer/commands/__init__.py`. Felmeddelandenas text
(`Fel: <kod>: <text>`) är en del av gränssnittet: facit-filerna och många tester jämför dem ordagrant.

## 3. Filformat in

- Bildfiler (PNG/JPG via OpenCV) som källa; kamera N via OpenCV.
- Punktfil (`calibrate PATH`): CSV med pixel och våglängd; mall `exempel/kalibrering/punkter_MALL.csv`.
- Linjefil (`toppar LINJEFIL`): CSV med kända linjer, `exempel/kalibrering/hg_linjer.csv`.
- Känd fördelning (`response build KNOWNFILE`): CSV, `exempel/kalibrering/lampa_A.csv`, `tests/kommandon/x12_kand.csv`.
- Kommandofil (`run FIL`, `--kor FIL`): textfil med en kommandorad per rad (`exempel/*.txt`, `exempel/demo/*.txt`,
  `tests/kommandon/testa_*.txt`).
- `rigg PATH`: JSON med fälten i `docs/rigg.md` (mall `exempel/rigg.json`).
- `response load FIL.npz`, `dark load FIL.npy`, `load MAPP` (en sparad mätmapp).

## 4. Filformat ut och utdatafiler

- Mätmapp `output_dir/ÅÅÅÅMMDD-HHMMSS[-N]/` (output_dir = `data` om inget annat sägs) med exakt
  `spectrum.csv`, `raw.png`, `settings.json`, `README.txt` (listan `SAVED_FILES` i `files.py`), därefter
  `spectrum.png`; `save --excel` ger även `spectrum_sv.csv`. Skrivs först som `.partial` och byter namn när allt är klart.
- `serie.csv` i `output_dir/NAMN/` vid mätserier.
- `snap-ÅÅÅÅMMDD-HHMMSS[-001].png`, `roi-ÅÅÅÅMMDD-HHMMSS.png` i output_dir; `image [FIL]` ger FIL (vägrar om den
  finns) eller `bild-ÅÅÅÅMMDD-HHMMSS.png` i output_dir (ändrat med Elias ja, BESLUT 10 och 15A; förut `bild.png` i cwd,
  som skrevs över).
- `response export PATH` (vägrar om filen finns sedan BESLUT 15A), `response save FIL.npz`, `dark save FIL.npy`,
  `calibrate save FIL.json`,
  `repeat N UT.csv`, `toppar LINJEFIL UT.csv`, `figure UT.png|UT.svg` (+ `UT.txt`), `series plot ... UT.png`,
  `history save FIL` (skriver aldrig över).
- `logs/spektro.log` (1 MB, 3 gamla) i cwd vid oväntade fel.
- `tools/gen_kommandon.py` skriver `docs/kommandon.md` och tabellen i README mellan `<!-- KOMMANDON START -->`
  och `<!-- SLUT -->`; `tools/felkatalog.py` skriver `docs/felkatalog.md`.

## 5. Namn som andra filer importerar eller pekar på

- Modulnamnen i `spectrometer/` (`calc, files, source, measure, meta, out, peaks, plot, quality, registry, roi, session,
  theme, display, main, analys, analysis.*, commands.*`): testerna importerar dem direkt, och
  `tests/test_architecture.py` låser lagerordningen och att `cv2` bara finns i `source`/`files`, `matplotlib` bara i
  `plot`/`analysis`, `print` bara i `out`.
- Kommandomodulerna listas som strängar i `FEATURES` (`spectrometer/commands/__init__.py`).
- `check_install.py` i roten (importeras av `tests/test_check_install.py` via `pythonpath = ["."]`),
  `tools/gen_kommandon.py`, `tools/felkatalog.py` (laddas av tester med sökväg).
- `tests/test_elias.py` är hjälpbibliotek för 29 testmoduler (FakeCamera, new_state m.fl.).
- `startskarm.prisma` (bara från `spektro.py`, valfritt).
- Repots filer som tester läser: `tests/data/bilder/rand_x12.png`, `tests/kommandon/*`, `tests/data/*`,
  `exempel/kalibrering/{hg_linjer,lampa_A,punkter_MALL}.csv`, `exempel/*.txt`, `exempel/rigg.json`, `exempel/demo/*.txt`,
  `docs/rigg.md`, `README.md` (måste innehålla `Topp 200 vid pixel 12 (1 bild)` och `- <rad>` för varje rad i
  `demo_cmds.LIMITS`), `CHANGELOG.md` (översta rubriken = `__version__`). Se KODKARTA 7.8–7.9.
- Pytest körs från repots rot (`pythonpath = ["."]`, `testpaths = ["tests"]`). CI: `ruff check .` och
  `pytest -q -p no:cacheprovider` på Ubuntu och Windows, Python 3.12.

## 6. Flyttat 2026-10-21 21:35 (Elias önskan, fas 8)

`demo/` och `kalibrering/` ligger nu i `exempel/`; alla hänvisningar i kod, tester, README och kommandofiler följde med (MANIFEST 17–18).
