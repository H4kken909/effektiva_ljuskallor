# Exempel: kommandofiler

En kommandofil är en rad per kommando, precis som vid prompten. Tomma rader hoppas över, och allt efter `#` är en
kommentar. Kör en fil från projektmappen med `run`:

```
spektro> run exempel/direkt.txt
```

`run` skriver varje rad som `spektro> RAD` före svaret och stannar vid första felet, med filen och radnumret sist:
`Fel: ... (exempel/direkt.txt rad 3)`. Raderna efter felet körs inte. `quit` i en fil avslutar programmet.

Utan prompt, till exempel i ett skript: `python -m spectrometer.main --kor exempel/direkt.txt --avsluta` ger slutkod 0, eller 1 om en rad gav `Fel:`. En fil `spektro-start.txt` i mappen där programmet startas körs före första prompten (bara vid en terminal, inte när indata pipas in).

| Fil | Vad den visar | Källa |
|---|---|---|
| `direkt.txt` | Direkt mätning: ROI, kanal, tre bilder, `step` och `save` | testbilden `rand_x12.png` |
| `kalibrera.txt` | Kedjan: mörker, kalibrering, respons och `response on` | testbilderna och `x12_500.csv`, `x12_kand.csv` |
| `transmission.txt` | Referens utan prov, `mode transmission`, provet ger T = 0,5 | `rand_x12.png` och `halv_x12.png` |
| `kalibrera_1_hitta.txt` | Toppar ur kameran och ett förslag till punktfil | kamera 0 |
| `kalibrera_2_anpassa.txt` | Kalibrering med punktfilen, `toppar` och `save` | kamera 0 |
| `rigg.json` | Mall för uppställningens data (`rigg rigg.json`, se `docs/rigg.md`) | – |

De tre första går på testbilderna i `tests/`, så de fungerar utan rigg. De två sista kräver kameran och
`kalibrering/punkter.csv` (se `kalibrering/README.md`).

Provat: `tests/test_kommandofiler.py` kör de tre första och kontrollerar toppen. Talen är relativa tal från kameran;
att filerna går igenom visar att räkningen stämmer, inte att instrumentet mäter rätt.
