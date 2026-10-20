# Snabbkort: mätkedjan

Ett A4. Skriv raderna efter `spektro> ` i ordning. `…` är ett tal som beror på riggen. Rigens värden (kameranummer, `roi`, punktfil) står i bruksanvisningen, avsnitt 2.

| # | Skriv | Du ska se |
|---|---|---|
| 1 | `python -m spectrometer.main` | `Skriv help för kommandona. quit eller Ctrl+D avslutar.` |
| 2 | `source camera 0` | `source camera 0` |
| 3 | `roi X Y W H` | `ROI:n kontrolleras vid nästa mätning.` och `roi X Y W H` |
| 4 | `frames 16` | `frames: 16` |
| 5 | `step` | `Topp … vid pixel … (16 bilder)`. Toppen 150 till 240, ingen rad `Varning: mättad` |
| 6 | `dark` (blockera ljusvägen först, ta bort kartongen efteråt) | `mörker: 16 bilder, medel …` |
| 7 | `calibrate PUNKTFIL` | `a0: …`, `a1: …`, `kontrollfel vid pixel …: …` |
| 8 | `step` | `Topp … vid våglängd (nm) … (16 bilder)` |
| 9 | `save` | `Sparad i data/ÅÅÅÅMMDD-HHMMSS` |
| 10 | `reference` (utan prov) | `Referens: 16 bilder, x från … till …` |
| 11 | `mode transmission` | `mode: transmission` |
| 12 | `step`, sedan `save` (provet i ljusvägen) | `Topp … vid våglängd (nm) … (16 bilder)` och `Sparad i data/ÅÅÅÅMMDD-HHMMSS` |

Direkt mätning är rad 1 till 9. Transmission är rad 10 till 12. Avsluta med `quit`.

## Om det går fel

1. `Fel: camera.open_failed …` eller `camera.read_failed`: annan USB-port eller annat kameranummer (`source camera 1`), stäng Teams och Kamera-appen, `python check_install.py --kamera 1`.
2. `Varning: mättad (255 i råbilden). Sänk exponeringen.` eller en mörk bild: ställ om exponeringen (README, Kamera), gör om rad 5, 6 och 10.
3. Programmet svarar inte: Ctrl+C. Annars stäng terminalen, dra ut USB-kabeln, starta om och börja på rad 1.

Alla tal är relativa counts, inte watt eller verkningsgrad.
