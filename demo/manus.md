# Demo-manus: mjukvarudelen (60 min)

Slutleverans fredag 2026-11-27, 15:15 till 17:00, P326 Pascal. Passets egentliga schema är inte känt: tiderna nedan är ett förslag på 60 minuter. Roller och namn är förslag som gruppen bestämmer.

Utskrifterna visar `…` där talet beror på riggen. Fyll i talen från riktiga körningar på uppställningen, aldrig från minnet.

## Roller

| Roll | Förslag | Gör |
|---|---|---|
| Skriver | Elias | alla kommandon, utom i delen där Jawad mäter |
| Riggen | Adrian | blockerar ljusvägen, byter prov, håller kameran |
| Pratar | Alan | förklarar vad som händer, håller tråden |
| Tar tid och noterar frågor | Isak | säger till vid varje tidsgräns och noterar frågor som inte står i `demo/fragor.md` |
| Uppställningen | Oscar | berättar om konstruktionen i första delen |

I delen där Jawad mäter skriver Jawad. Elias eller Adrian coachar.

## Tidsplan

| Tid | Min | Moment | Pratar | Skriver | Skärmen ska visa |
|---|---|---|---|---|---|
| 0:00 | 5 | Översikt: vad programmet gör och inte | Alan, Oscar | inget | bilden Begränsningar (nedan) |
| 0:05 | 10 | Kalibrering och mörker | Adrian förklarar | `run demo/1_forbered.txt`, `dark`, `run demo/2_kalibrera.txt` | `källa: kamera 0`, `mörker: 16 bilder, medel …`, `kontrollfel vid pixel …: … ` |
| 0:15 | 10 | Direkt mätning och transmission | Alan | `run demo/3_mata.txt`, `reference`, `mode transmission`, `run demo/3_mata.txt` | `Topp … vid våglängd (nm) … (16 bilder)`, `Referens: 16 bilder, x från … till …`, `mode: transmission` |
| 0:25 | 5 | Lagring och Excel | Elias | `save` (om inte redan gjort) | `Sparad i data/ÅÅÅÅMMDD-HHMMSS`, sedan `spectrum.csv` importerad i Excel |
| 0:30 | 15 | Jawad mäter själv | Jawad, med coachning | `dark`, `reference`, `mode transmission`, `step`, `save` | samma rader som ovan |
| 0:45 | 5 | Begränsningar och felkällor | Oscar, Alan | inget | bilden Begränsningar |
| 0:50 | 10 | Frågor | alla | efter behov | `demo/fragor.md` finns till hands |

`run` stannar vid första raden som ger `Fel:` och skriver fil och radnummer sist på raden: se `demo/README.md`, Så körs en fil.

## Före passet

- Lampan har varit på i 10 minuter. Kameran är låst: exponering och gain noterade.
- Kartongen för `dark` ligger framme. Skärmens ljus är riktat bort från uppställningen.
- `show` visar `källa: kamera 0` och `frames: 16`.
- Går något fel: `demo/README.md`, Reservplan. Efter tre minuter utan bild går vi till nästa nivå.

## Begränsningar och felkällor (en bild)

- 8 bitar per färg. Webbkameran lämnar inte ut sensorns råvärden.
- Gamma, vitbalans och autoexponering är avstängda. Exponering och gain är låsta för hela mätningen.
- Mättnad (255) ger fel tal. Programmet varnar men markerar inte positionen i filen.
- Kalibreringen gäller bara där optiken inte flyttats, och bara inom det giltiga intervallet.
- Programmet minns inget: mörker, kalibrering och referens görs om efter varje start.
- Alla tal är relativa counts, inte watt, lumen eller verkningsgrad.
- Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.
