# Bruksanvisning: webbkameraspektrometern

Version 1. Skriven mot programmet 1.0.41 och mot testbilder. Den är inte provad på uppställningen. Adrian följer den ordagrant som en ny användare på riggen och rättar texten där han fastnar; det blir version 2.

Utskrifterna nedan visar `…` där talet beror på riggen. Talen fylls i från riktiga körningar, aldrig från minnet.

## 1 Vad programmet gör och inte gör

Programmet gör en bild från en webbkamera (eller en bildfil) till ett spektrum: en kurva av signal mot våglängd. Det kan

- mäta direkt ljus från en källa,
- mäta transmission, alltså hur mycket ljus ett prov släpper igenom,
- dra bort mörkerbrus och rätta för kamerans känslighet,
- spara resultatet som filer som går att öppna i Excel.

Det kan inte mäta effekt i watt, ljusflöde i lumen eller verkningsgrad. Kamerans tal är relativa counts. Programmet ställer inte kamerans exponering och minns ingenting mellan två starter. Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.

## 2 Starta

Värdena för just den här uppställningen (fylls i på riggen):

| Värde | Kommando | På riggen |
|---|---|---|
| Kameranummer | `source camera N` | |
| Bandet där spektrumet ligger | `roi X Y W H` | |
| Färgkanal | `channel gray` | gray |
| Exponering och gain | låses utanför programmet (README, Kamera) | |
| Punktfil för kalibrering | `calibrate PUNKTFIL` | |

Windows (PowerShell):

```powershell
cd C:\spektro
.\.venv\Scripts\Activate.ps1
python -m spectrometer.main
```

Arch: `source .venv/bin/activate` i stället för raden med `Activate.ps1`.

Programmet svarar `Skriv help för kommandona. quit eller Ctrl+D avslutar.` och väntar vid `spektro>`. `help` listar kommandona, `help roi` visar hur `roi` skrivs, `quit` avslutar.

Kontrollera kameran och exponeringen:

```
source camera 0
step
```

Svaret är `Topp … vid pixel … (1 bild)`. Toppen ska ligga mellan 150 och 240. Står det `Varning: mättad (255 i råbilden). Sänk exponeringen.` är den för hög: sänk exponeringen (README, Kamera) och mät om.

`roi` är bandet av bilden där spektrumet ligger, i pixlar: `roi X Y W H`, eller `roi full` för hela bilden. Ett band över flera rader ger mindre brus än en enda rad. Programmet svarar på `source` och `roi` med kommandot i kommandoform (`roi 0 200 640 40`, `roi full`) och på de andra inställningarna med `frames: 16`.

## 3 Mäta direkt

Lampan ska ha varit på i 10 minuter. Kameran är låst och rummet mörkt.

1. Ställ in: `source camera 0`, `roi X Y W H`, `channel gray`, `frames 16`. `frames 16` medelvärdesbildar 16 bilder per mätning.
2. Kontrollera exponeringen med `step` (toppen 150 till 240, ingen varning om mättnad).
3. Mörker: blockera ljusvägen helt (kartong över ljusvägen) och skriv `dark`. Svaret är `mörker: 16 bilder, medel …`. Ta bort kartongen. Säger programmet `Varning: mörkret liknar bilden. Var ljusvägen blockerad?` var ljusvägen inte blockerad: mät om.
4. Kalibrera: `calibrate PUNKTFIL`. Svaret är raderna `a0: …`, `a1: …`, `anpassat: pixel … till …`, `giltigt: pixel … till …`, en `residual: …` per punkt och `kontrollfel vid pixel …: …`. Står det `Varning: kontrollfelet … nm är större än steget … nm.` är kalibreringen för dålig: kontrollera pixelnumren i filen.
5. Mät: `step`. Svaret är `Topp … vid våglängd (nm) … (16 bilder)`.
6. Spara: `save`. Svaret är `Sparad i data/ÅÅÅÅMMDD-HHMMSS`.

Punktfilen är en CSV med rubriken `pixel,wavelength_nm,check`. Rader med `check` 0 anpassar linjen, rader med 1 kontrollerar den; gruppens minimum är fyra anpassningspunkter och en kontrollpunkt (programmet godtar färre för grad 1), och kontrollpunkten ska ligga mitt i intervallet. Pixelnumren tar du från en lampa med kända linjer, till exempel ett lysrör:

| Kvicksilverlinje | Våglängd (nm) | Pixel (mäts på riggen) |
|---|---|---|
| violett | 404,656 | |
| blå | 435,833 | |
| grön | 546,074 | |
| gul | 576,960 | |
| gul | 579,066 | |

Så hittar du en linjes pixel: sätt `roi` smalt runt linjen, till exempel 40 pixlar bred, och kör `step`. Svaret `Topp … vid pixel N` ger linjens pixel N. Sätt tillbaka `roi` till hela bandet när du är klar.

Känslighetskorrigering (`response build KANDFIL` och `response on`) kräver en lampa med känd fördelning. Vilken lampa det blir är inte avgjort (README, Öppna punkter). Filen ska täcka hela det uppmätta våglängdsintervallet med lite marginal åt båda hållen: positioner utanför blir ogiltiga, och programmet säger `respons: N av M positioner giltiga`.

## 4 Transmission

Gör avsnitt 3 steg 1 till 4 först: ställ in, mörker och kalibrering.

1. Ta bort provet. Skriv `reference`. Svaret är `Referens: 16 bilder, x från … till …`.
2. Skriv `mode transmission`. Svaret är `mode: transmission`. Står det `ingen referens, kör reference först` saknas steg 1.
3. Sätt in provet i ljusvägen och skriv `step`. Talet är kvoten mellan prov och referens: 1 betyder att allt ljus släpps igenom. Värden strax över 1 är brus, så programmet varnar först över 1,05. Står det `Varning: transmission över 105 % på N positioner (…)` har något ändrats sedan referensen (lampa, exponering eller kamerans läge): mät referensen om.
4. `save`. Då får `spectrum.csv` också kolumnen `absorbance`.
5. `mode direct` tar dig tillbaka till direkt mätning.

Ändrar du `channel`, bandets läge i sidled eller bredd i `roi`, eller kalibreringen efter `reference`, svarar `step` med ett fel som slutar `kör reference igen`. Gör det. Ändrar du bara höjden på `roi` märker programmet inget: kör `reference` igen ändå. Tar du om `dark` försvinner referensen, och programmet säger det.

## 5 Spara och öppna i Excel

`save` skriver en mapp med tid och datum under `data/`, till exempel `data/ÅÅÅÅMMDD-HHMMSS`, med fem filer:

- `README.txt`: vad mappen innehåller och vad kolumnerna betyder.
- `spectrum.csv`: kolumnerna `x_px` (eller `x_nm` när en kalibrering finns), `value`, `valid` och vid transmission `absorbance`. `value` är det korrigerade värdet i relativa counts, inte råa counts.
- `raw.png`: den sista bilden som lästes, avkodad till 8 bitar. Det är inte sensorns rådata.
- `settings.json`: inställningarna som gällde.
- `README.txt`: en kort förklaring av filerna och kolumnerna, och raderna om just den här mätningen (källa, kanal, läge, programversion).
- `spectrum.png`: rapportfiguren ur mätningen i ljust tema, med mätmappen och inställningarna i rubriken.

Dubbelklicka inte på `spectrum.csv`: svenskt Excel läser `1.5` som ett datum. Öppna i stället Data, Från text/CSV, välj avgränsare Komma och språk Engelska (USA). I Calc: Arkiv, Öppna, avgränsare Komma, teckenkodning UTF-8, språk Engelska (USA).

För en serie: `save data/led_rod_20mA` lägger en tidsstämplad mapp i `data/led_rod_20mA`. Använd en mapp per diod. På ett USB-minne: `save E:/mat` (Windows) eller `save /run/media/ANVÄNDARE/NAMN/mat` (Arch). Skriv alltid snedstreck, aldrig bakslag. Kontrollera att mappen syns i Utforskaren och mata ut minnet innan du drar ut det.

## 6 Felsökning

| Du ser | Orsak och åtgärd |
|---|---|
| `Fel: camera.open_failed: kunde inte öppna …` | Fel kameranummer, kabeln lös eller något annat program (Teams, Kamera-appen) håller kameran. Resten av felraden säger vad du ska prova på just ditt system (Windows: sekretessinställningen för kameran; Linux: `/dev/video0` och `v4l2-ctl`). Prova `source camera 1` och `python check_install.py --kamera 1`. |
| `Fel: camera.read_failed …` | Kameran tappade kontakten. Dra ut USB-kabeln, sätt i den och skriv `source camera N` igen. |
| `Varning: mättad (255 i råbilden). Sänk exponeringen.` | Sänk exponeringen och gör om `dark` (och `reference`). |
| `Varning: mörkret liknar bilden …` | Ljusvägen var inte blockerad under `dark`. Gör om det. |
| `Fel: input.missing_data: inget mörker, kör dark först` | Samma sorts rader säger `ingen kalibrering, kör calibrate först`, `ingen referens, kör reference först` och `Ingen mätning än. Kör step först.` Gör det som står. |
| Fönstret syns inte | Det kan ligga bakom terminalen: Alt+Tab. |
| Programmet svarar inte | Ctrl+C. Hjälper det inte: README, Om kameraläsningen hänger. Uppsättningen försvinner och görs om. |
| `save` ger `[WinError 5]` | Antivirus eller OneDrive låser mappen. Spara till en annan mapp, till exempel `save C:/spektro-test`. |
| Ett kommando med sökväg beter sig konstigt | Skriv snedstreck (`data/mat`), och citattecken om sökvägen har blanksteg: `source file "data/min bild.png"`. |

## 7 Begränsningar och felkällor

- Bilden är 8 bitar per färg. Webbkameran lämnar inte ut sensorns råvärden, så `raw.png` är en avkodad bild.
- Kamerans gamma, vitbalans och autoexponering ska vara avstängda och exponering och gain låsta. Programmet kontrollerar inte det och ställer dem inte.
- Mättnad (255) ger fel tal. Programmet varnar i `step`, men markerar inte positionen i filen.
- Kalibreringen gäller bara där optiken inte har flyttats, och bara inom det giltiga intervallet som `calibrate` skriver.
- Programmet minns inget: mörker, kalibrering och referens görs om efter varje start, och efter varje ändring av exponering eller uppställning.
- Alla tal är relativa. De är inte watt, lumen eller verkningsgrad, och två olika kameror eller exponeringar går inte att jämföra.
- Upplösningen i nm bestäms av spalt och optik: fylls i från Adrians test.
- Om kameran ser infrarött beror på kamerans filter: fylls i.
- Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.
