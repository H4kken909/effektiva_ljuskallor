# Riggen: uppställningens konstruktionsdata (Krav 9)

Krav 9: uppställningens konstruktionsdata ska följa mätningen. Fyll i `rigg.json` vid riggen, en gång per
uppställning och igen när något flyttas eller byts. Programmet läser filen med `rigg rigg.json`, och `save` skriver
den i varje mätmapps `settings.json` (nyckeln `rigg`, före `coefficients`).

## Så gör du

1. Kopiera mallen: `Copy-Item exempel\rigg.json rigg.json` (Arch: `cp exempel/rigg.json rigg.json`).
2. Mät och fyll i fälten nedan. Okänt får stå som `null`; programmet säger vilka fält som är tomma.
3. Vid prompten: `rigg rigg.json`. `rigg` ensam visar vilken fil som gäller, `rigg off` tar bort den.
4. Ta ett foto av uppställningen och skriv filnamnet i `photo`.

Lägg gärna `rigg rigg.json` i `spektro-start.txt`, så läses den varje gång programmet startas vid riggen.

## Fälten

| Fält | Vad | Exempel |
|---|---|---|
| `date` | datum då uppställningen mättes | `"2026-11-03"` |
| `slit_width_um` | spaltbredd i mikrometer | `100` |
| `grating_lines_per_mm` | gittret, linjer per mm | `1000` |
| `grating_camera_distance_mm` | avstånd gitter till kamera i mm | `45` |
| `angle_deg` | vinkel mellan ljusets riktning och kameran i grader | `30` |
| `camera_model` | kamerans modell | `"Logitech C270"` |
| `resolution` | upplösning som i `info`, bredd x höjd | `"640x480"` |
| `lamp` | lampan som mäts eller kalibreras med | `"lysrör, Hg-linjer"` |
| `filter` | filter i ljusvägen, eller `"inget"` | `"ND 1.0"` |
| `photo` | filnamn på fotot av uppställningen | `"rigg-2026-11-03.jpg"` |
| `note` | allt annat: vad som ändrats sedan sist | `"spalten flyttad 2 mm"` |

Talen är konstruktionsdata: de beskriver uppställningen, programmet räknar inte med dem.
