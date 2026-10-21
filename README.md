# Effektiva ljuskällor: spektrometern

Programmet gör en kamerabild (eller en bildfil) av ett spektrum till en spektralkurva: i pixlar, eller i nm efter
kalibrering, med mörkeravdrag, responskorrigering och transmission. Kursen TFYY51 vid Linköpings universitet,
grupp GRYb1. Allt är relativt: kameran ger counts, inte watt eller lumen.

## Installation

Python 3.12 (se `.python-version`). I projektmappen:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt   (Windows)
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt           (Linux)
python check_install.py
```

`check_install.py` kontrollerar Python, miljön, biblioteken, kamerastödet och Tk. `python check_install.py --kamera N`
provar kamera N. På Arch kan `bash arch_start.bash` göra installationen och skriva launchern `./spektro`.

## Körning

- `python spektro.py`: startskärm i maximerat fönster och sedan prompten (`--no-splash` hoppar över startskärmen).
- `python -m spectrometer.main`: prompten `spektro>` direkt. `help` listar kommandona, `quit` avslutar.
- `python -m spectrometer.main BILD`: mäter en bildfil en gång, sparar och ritar.
- `python -m spectrometer.main --kor FIL --avsluta`: kör en kommandofil (som `run FIL`) och avslutar.
- `python -m spectrometer.analys KOMMANDO MAPP`: räkna på en sparad mätmapp utan prompt och kamera.

Sökvägar skrivs med `/`. Programmet minns inget mellan två starter: `dark`, `calibrate`, `response build` och
`reference` körs om efter varje start.

## Snabbstart

Tre kommandon på en testbild, utan kamera:

```
spektro> source file tests/data/bilder/rand_x12.png
source file tests/data/bilder/rand_x12.png
spektro> step
Topp 200 vid pixel 12 (1 bild)
spektro> save
Sparad i data/20261020-102233
```

Fick du `Topp 200 vid pixel 12 (1 bild)` fungerar installationen. Det visar att räkningen stämmer på en testbild, inte
att kameran eller uppställningen mäter rätt.

## Kommandon

Tabellen fylls av `python tools/gen_kommandon.py` ur koden (`--check` säger om den är aktuell).

<!-- KOMMANDON START -->
| kommando | syntax | vad |
|---|---|---|
| help | help [KOMMANDO] | Kommandot help [KOMMANDO]: en rad per kommando i registret, eller raden och syntaxen för ett kommando. |
| quit | quit | Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True); frågar först om en osparad mätning. |
| show | show | Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns. |
| status | status | Kommandot status: mörker, kalibrering, respons, referens och läge på en rad, sedan nästa steg i kedjan. |
| version | version | Kommandot version: programmet, Python, biblioteken, git och operativsystemet på en rad. |
| source | source file PATH eller source camera N | Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden. |
| roi | roi X Y W H eller roi full | Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden, eller inte lämnar plats åt background N, ger fel och den gamla står kvar. |
| channel | channel gray, sum, red, green eller blue | Kommandot channel NAMN: färgkanal ur calc.CHANNELS. |
| axis | axis horizontal eller axis vertical | Kommandot axis RIKTNING: riktning ur session.AXES. |
| frames | frames N | Kommandot frames N: antalet bilder per mätning, från 1 till registry.MAX_FRAMES (1000). |
| info | info | Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen. |
| cameras | cameras | Kommandot cameras: provar kameranummer 0 till 4 med source.probe och skriver en rad per nummer. Källan ändras inte. |
| snap | snap | Kommandot snap [N]: läser N bilder ur källan och sparar dem som PNG; state ändras inte. |
| image | image | Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger. |
| step | step | Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1,05. |
| save | save [DIR] [--excel] | Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir. |
| start | start [SEKUNDER] | Kommandot start [SEKUNDER]: spektrumet live tills Ctrl+C, tills fönstret stängs eller efter SEKUNDER. |
| stability | stability | Kommandot stability [N]: N bilder i rad med samma källa; skriver hur toppvärdet varierar och driver. |
| perf | perf | Kommandot perf [N]: N mätningar med nuvarande källa, ROI, kanal och frames, utan fönster; skriver tiderna. |
| calibrate | calibrate PATH [DEGREE [MARGIN]] | Kommandot calibrate PATH [DEGREE [MARGIN]]: anpassar våglängden till punktfilen och prövar mot kontrollpunkterna. |
| toppar | toppar | Kommandot toppar [N]: de N högsta topparna (efter calibrate även nm); toppar LINJEFIL [UT.csv]: punktfilsförslag. |
| dark | dark [N] | Kommandot dark [N]: mörkret som medel av N bilder (CAPTURE_FRAMES utan N). Det gamla står kvar vid fel. |
| response | response build KNOWNFILE [N], response on, response off eller response export PATH | Kommandot response build KNOWNFILE [N], response on, response off eller response export PATH. |
| reference | reference [N] eller reference check [N] | Kommandot reference [N]: referensen utan prov, utan respons och transmission, sparad med kanalen. |
| mode | mode direct eller mode transmission | Kommandot mode direct eller mode transmission (transmission kräver en referens). |
| run | run FIL | Kommandot run FIL: kör raderna i FIL som om de skrevs vid prompten, och skriver spektro> RAD före svaret. |
| wait | wait SEKUNDER | Kommandot wait SEKUNDER: väntar 1 till MAX_WAIT hela sekunder; Ctrl+C avbryter (main skriver Avbrutet.). |
| reset | reset eller reset ja | Kommandot reset [ja]: ny state med DEFAULTS. I en terminal frågar det först om något går förlorat; undo ångrar. |
| undo | undo | Kommandot undo: lägger tillbaka state från före senaste ändrande raden vid prompten; mätningen glöms. |
| history | history [N] | Kommandot history [N]: de N senaste raderna som skrevs vid prompten, numrerade från början av sessionen. |
| history save | history save FIL | Kommandot history save FIL: raderna utan fel och inte ångrade, utan NOT_SAVED, i en ny kommandofil. |
| clear | clear dark, clear calibration, clear response, clear reference eller clear all | Kommandot clear NAMN: tar bort mörker, kalibrering, respons, referens, eller allt utom inställningarna. |
| set | set min_response TAL, set min_reference TAL eller set output_dir MAPP | Kommandot set NYCKEL VÄRDE för min_response och min_reference (ändliga tal över 0) och output_dir. |
| rows | rows, rows mean eller rows median | Kommandot rows [mean\|median]: medel (calc.extract_spectrum) eller median (calc.extract_median) över raderna. |
| background | background, background N eller background off | Kommandot background [N\|off]: medianen av N rader på var sida om ROI:n dras av efter mörkret. |
| response save | response save FIL.npz | Kommandot response save FIL.npz: x, values, roi, channel, axis, coefficients och pixel_range med np.savez. |
| response load | response load FIL.npz | Kommandot response load FIL.npz: som response build, men responsen läses ur filen; response on behövs sedan. |
| dark save | dark save FIL.npy | Kommandot dark save FIL.npy: mörkret, (H, W, 3) i counts, med np.save som float32 (halva filen). 1.2.14. |
| dark load | dark load FIL.npy | Kommandot dark load FIL.npy: som dark, men mörkret läses ur filen. 1.2.14. |
| rigg | rigg, rigg PATH eller rigg off | Kommandot rigg [PATH\|off]: läser rigg.json (fälten i docs/rigg.md) till state["rigg"]; save skriver den. DOK-31. |
| theme | theme | Kommandot theme light eller theme dark: färgerna i nästa fönster (start, graf). |
| view | view | Kommandot view: vad nästa fönster (start, graf) visar. Ändrar bara visningen, aldrig en mätning. |
| graf | graf | Kommandot graf: senaste mätningen med samma rubrik och rutor som live, i ett fönster som väntar tills det stängs. |
| roi show | roi show | Kommandot roi show: kopia av senaste bilden med ROI-rutan och mättade pixlar i magenta; sökvägen skrivs. |
| roi auto | roi auto | Kommandot roi auto: skriver ett förslag; du godtar det genom att skriva raden. |
| roi profile | roi profile | Kommandot roi profile: tre rader om bandet tvärs spektrumet (rader vid horizontal, kolumner vid vertical). |
| roi band | roi band | Kommandot roi band START WIDTH: rader START till START+WIDTH vid horizontal, kolumner vid vertical. |
| roi move | roi move | Kommandot roi move DX DY: flyttar ROI:n; kontrolleras mot senaste bilden som roi X Y W H. |
| axis detect | axis detect | Kommandot axis detect: vågrätt eller lodrätt band ur de ljusa pixlarnas rektangel; skriver ett förslag. |
| exposure | exposure N | Kommandot exposure N: exponeringen som sätts varje gång kameran öppnas. Kör auto off först. |
| gain | gain N | Kommandot gain N: förstärkningen som sätts varje gång kameran öppnas. |
| auto | auto on eller auto off | Kommandot auto on eller auto off: med auto på ändrar kameran exponeringen själv, och då går serier inte att jämföra. |
| note | note [TEXT...] eller note clear | Kommandot note TEXT: fri text till settings.json (och serie.csv) vid varje save, tills den byts. Mätningen står kvar. |
| series start | series start NAMN | Kommandot series start NAMN: mätmapparna i output_dir/NAMN och en rad per save i serie.csv där; finns den fortsätter den. |
| series note | series note current_mA=20 voltage_V=2.9 led=röd | Kommandot series note NYCKEL=VÄRDE...: ström, spänning, LED, prov och lampa till varje save tills de byts. |
| series stop | series stop | Kommandot series stop: skriver hur många rader serien fick och glömmer series note. Mätningen står kvar. |
| series plot | series plot NAMN... [--x current\|voltage] [--droop] [UT.png\|UT.svg] | Kommandot series plot NAMN...: area mot ström (Krav 18), eller med --droop area/I delad med sitt max (Krav 21). |
| load | load MAPP | Kommandot load MAPP: spectrum.csv och settings.json ur mätmappen blir senaste mätningen; skriver toppen som step. |
| fwhm | fwhm [N] | Kommandot fwhm [N]: topparna i senaste mätningen med linjebredd vid halva höjden, och arean under kurvan. |
| compare | compare MAPP... [--norm] | Kommandot compare MAPP... [--norm]: en rad per mapp och kurvorna i ett fönster (Krav 17a och 17b). Ändrar inte state. |
| figure | figure UT.png [MAPP...] [--norm] [--xlim MIN MAX] [--log] [--ev] [--cie] | Kommandot figure UT.png\|UT.svg: senaste mätningen, eller mapparna i samma axlar, som egen figur till rapporten. |
| color | color | Kommandot color: x, y, färgtemperatur (CCT och Duv, 1.2.15) och relativ ljusstyrka ur senaste mätningen. |
| mix | mix MAPP_R MAPP_G MAPP_B --target X Y, --cct K, --sweep eller --fwhm W | Kommandot mix MAPP_R MAPP_G MAPP_B och ett val: vikterna som blandar tre LED-mätningar till en färg (Krav 19). |
| bandgap | bandgap [MAPP] [--anpassa] | Kommandot bandgap [MAPP] [--anpassa]: E_g i eV och nm, om kanten ligger i fönstret 366–766 nm, och osäkerheten. |
| repeat | repeat N [UT.csv] | Kommandot repeat N [UT.csv]: N mätningar i rad med samma källa och inställningar; senaste mätningen står kvar. |
| linearity | linearity E1 E2 E3 [E4 ...] | Kommandot linearity E1 E2 E3 [E4 ...]: en mätning per exponering, arean och avvikelsen från en rät linje. |
| calibrate save | calibrate save FIL.json | Kommandot calibrate save FIL.json: kalibreringen med residualer, kontrollfel, rms, nm per pixel och upplösning. |
| guide | guide | Kommandot guide: källa, ROI, mörker, kalibrering, respons, mätning och sparad, med x för det som är gjort. |
| pause | pause TEXT | Kommandot pause TEXT: skriver TEXT och väntar på Enter i en terminal; avbryt stoppar kommandofilen. |
| help limits | help limits | Kommandot help limits: en rad per begränsning i LIMITS (samma rader som i README, Begränsningar). |
<!-- SLUT -->

## Så sparas en mätning

`save` skriver en mapp med tid och datum under `data/` (eller `--output DIR`): `spectrum.csv`, `raw.png`,
`settings.json`, `README.txt` och `spectrum.png`. `load MAPP`, `compare`, `figure` och analysskriptet läser tillbaka dem.

## Dokument och mappar

- `docs/bruksanvisning.md`: bruksanvisningen för en läsare som inte kan programmet. `docs/snabbkort.md`: mätkedjan på
  ett A4. `docs/kommandon.md`: kommandoreferensen. `docs/rigg.md`: fälten i riggfilen. `docs/matpass-mall.md`: mall
  för ett mätpass.
- `exempel/`: kommandofiler för direkt mätning, kalibrering och transmission, och mallen `rigg.json`.
- `kalibrering/`: kända linjer (`hg_linjer.csv`), en känd lampa (`lampa_A.csv`) och mallen för punktfilen.
- `demo/`: kommandofilerna och dokumenten för demon; läs `demo/README.md` först.
- `tests/`: testerna (`python -m pytest -q -p no:cacheprovider`), Adrians kommandofiler med facit i `tests/kommandon/`.
- `dev/`: allt som bara utvecklingen behöver (kontrollskript, baslinje, protokoll, verktyg, gamla skript). Se
  `dev/README.md`. Den gamla, långa README:n ligger i `dev/README-gammal.md`.
- `CHANGELOG.md`: versionerna.

## Begränsningar

Samma rader som `help limits` skriver i programmet (`tests/test_demoflode.py` kontrollerar att de är lika):

- Intensiteten är relativ: kameran ger counts, inte watt, lumen eller verkningsgrad.
- 8 bitar: varje pixel är 0–255; vid 255 är den mättad och toppen blir för låg (step varnar).
- Fönstret är 366–766 nm med KO-kalibreringen: utanför finns ingen kalibrerad våglängd.
- Upplösningen är FWHM för en smal linje (laser eller lysrörets 576,96 och 579,07 nm); calibrate save skriver den.
- Färg och färgtemperatur kräver response on; färgtemperaturen gäller bara nära svartkroppskurvan.
- Bandgapet är brantaste lutningen extrapolerad till A = 0; osäkerheten är bara ±0,5 pixelsteg.
- Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.
