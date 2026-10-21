# Mätpass: protokoll (mall)

Ett blad per mätpass. Skriv ut, fyll i för hand vid riggen och lägg en bild av bladet i gruppens delade mapp.
Aldrig ensam i labbet: minst två personer under hela passet (Krav 26).

## Före passet

| Vad | Ifyllt |
|---|---|
| Datum och tid |  |
| Personer (minst två) |  |
| Källa och diod-ID (eller lampa) |  |
| Ström och spänning, multimeterns typ och noggrannhet |  |
| Extern effektmätare eller luxmeter: typ, våglängdsområde, kalibreringsdatum |  |
| Kamera, exponering och gain (`info`; Arch: `v4l2-ctl --list-ctrls`) |  |
| Lampa och filter i ljusvägen |  |
| Rigg: `rigg rigg.json` inläst, ändringar sedan sist (`docs/rigg.md`) |  |
| ROI, kanal, frames (`show`) |  |

Laser: aldrig rakt in i spalten utan dämpning. Använd diffus spridning eller gråfilter och kortaste exponering. En laser
mättar kameran direkt (`Varning: mättad`), och dess våglängd är nominell.

## En rad per `save`

| Tid | Mappnamn i `data/` | settings_id | Prov eller lampa | Anmärkning (mättnad, drift, varningar) |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

Mappnamnet står i raden `Sparad i data/...`, `settings_id` i mätmappens `settings.json`.

## Efter passet

- [ ] Kopiera mätdata (skripten ligger på grenen `dev`): `.\dev\verktyg\kopiera-data.ps1 D:\matdata` (Windows) eller `bash dev/verktyg/kopiera-data.sh /run/media/$USER/USB/matdata` (Arch). En kopia på USB-minnet och en i gruppens delade mapp.
- [ ] Antal nya mätmappar som skriptet skrev stämmer med raderna ovan.

Förslag: mätmapparna (`spectrum.csv`, `settings.json`, `raw.png`) kan också committas till ett eget privat repo,
till exempel `ljuskallor-matdata`, ett pass per commit. Inte i kodrepot: där står `data/` i `.gitignore`.

Talen i mätmapparna är relativa tal från kameran. Ett pass som går igenom visar att räkningen stämmer, inte att
instrumentet mäter rätt; det avgör jämförelsen med de externa mätarna ovan.
