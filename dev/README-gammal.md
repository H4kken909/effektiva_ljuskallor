# Effektiva ljuskällor: spektrometern

Programmet gör en kamerabild (eller en bildfil) av ett spektrum till en spektralkurva: i pixlar, eller i nm efter
kalibrering, med mörkeravdrag, responskorrigering och transmission. Kursen TFYY51 vid Linköpings universitet,
grupp GRYb1, mjukvarudelen av Delrapport 2. Grenen `adrianfemboygaming` är den som lämnas in, och `v1.0.0` är den
frysta versionen.

Paketet `spectrometer` har fem filer:

| Fil | Ansvar |
|---|---|
| `calc.py` | All räkning (bara NumPy) |
| `source.py` | Läser bilder från en fil eller kameran |
| `plot.py` | Ritar spektrumet |
| `files.py` | Skriver mätmappen och läser punktfiler och kända fördelningar |
| `main.py` | Prompten och kommandona; den enda filen som importerar de andra fyra |

## Installation

Python 3.12 (`.python-version` är committad, så `uv` väljer versionen själv), en virtuell miljö i `.venv` och
biblioteken i `requirements.txt` och `requirements-dev.txt`. Klona till en mapp utan mellanslag och utan å, ä och ö i
sökvägen (se Öppna punkter).

Windows (PowerShell), Windows 10 och 11, Intel/AMD och ARM:

1. `winget install --id Git.Git -e`
2. `winget install --id astral-sh.uv -e` (stäng PowerShell och öppna ett nytt fönster efteråt, så att `git` och `uv` hittas)
3. `git clone https://github.com/H4kken909/effektiva_ljuskallor.git`
4. `cd effektiva_ljuskallor`
5. `git switch adrianfemboygaming`
6. `uv python install cpython-3.12-windows-x86_64-none`
7. `uv venv --seed --python cpython-3.12-windows-x86_64-none`
8. `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (första gången, svara `Y`), sedan `.\.venv\Scripts\Activate.ps1`
9. `uv pip install -r requirements.txt -r requirements-dev.txt`
10. `python check_install.py`

Steg 6 och 7 väljer x64-Python med flit. På Intel/AMD är det den vanliga Pythonen. På Windows ARM (till exempel
Snapdragon) körs den genom Windows inbyggda emulering, och det krävs där: `opencv-python` har inget paket för Windows
ARM64, så med ARM-Python försöker pip bygga OpenCV själv och stannar med `Unknown compiler(s)`. Kontroll:
`python -c "import sys, sysconfig; print(sysconfig.get_platform(), sys.executable)"` ska skriva `win-amd64` och en
sökväg som slutar med `.venv\Scripts\python.exe`. Är repot privat behöver `git clone` en inloggning: GitHub öppnar en
webbläsare första gången, eller `winget install --id GitHub.cli -e` och `gh auth login`.

Arch Linux (bash):

1. `sudo pacman -S --needed git uv tk base-devel psmisc v4l-utils guvcview`
2. `git clone https://github.com/H4kken909/effektiva_ljuskallor.git`
3. `cd effektiva_ljuskallor`
4. `git switch adrianfemboygaming`
5. `uv python install 3.12`
6. `uv venv --seed`
7. `source .venv/bin/activate`
8. `uv pip install -r requirements.txt -r requirements-dev.txt`
9. `python check_install.py`

`tk` behövs för Matplotlibs fönster, `v4l-utils` för `v4l2-ctl` (kamerans reglage) och `psmisc` för `fuser`, som visar
vem som håller kameran.

`check_install.py` kontrollerar att Python är 3.12, att `.venv` är aktiv, att biblioteken i requirements-filerna går
att importera och att OpenCV har kamerastöd (V4L2 på Linux, DirectShow på Windows). Den skriver en rad `OK` eller `FEL`
per kontroll och sist `Installationen stämmer.`; ett `FEL` säger vad som saknas. `python check_install.py --kamera N`
öppnar dessutom kamera N och läser några bilder (`--bilder K` ändrar antalet).

Varje ny terminal: `cd` till projektmappen och aktivera miljön, `.\.venv\Scripts\Activate.ps1` på Windows och
`source .venv/bin/activate` på Arch. Prompten börjar då med `(.venv)`.

Vanliga fel:

| Fel | Orsak | Åtgärd |
|---|---|---|
| `The module '..venv' could not be loaded` | Aktiveringsraden felskriven | Skriv exakt `.\.venv\Scripts\Activate.ps1` |
| `running scripts is disabled on this system` | PowerShell stoppar skript | Steg 8, `Set-ExecutionPolicy` |
| `Unknown compiler(s)` när `opencv-python` installeras | ARM64-Python i miljön | Ta bort `.venv` (`Remove-Item -Recurse -Force .venv`) och gör om steg 6 och 7 |
| `No module named numpy` (eller `matplotlib`, `cv2`) | Miljön inte aktiverad, eller steg 9 misslyckades | Aktivera, gör om steg 9 |
| `Repository not found` vid `git clone` | Inbjudan till repot inte godkänd, eller fel konto | Godkänn inbjudan, kontrollera `gh auth status` |
| `FEL  Python 3.x` från `check_install.py` | Fel Python i miljön | Ta bort `.venv` och gör om steg 6 och 7 (Arch: 5 och 6) |

## Körning

`py -m spektro` (Windows) eller `python3 -m spektro` (Linux, inte provat än) i projektmappen startar samma
program med startskärm: maximerat fönster, prismat och fyra gula rader, sedan prompten. Första gången byggs
`.venv` och `requirements.txt` installeras, så ingen behöver aktivera miljön. `--windowed` lämnar fönstret som
det är, `--no-splash` går direkt till prompten och `--delay SEK` ändrar pausen mellan raderna. Utan terminal
(pipad in- eller utmatning) blir utskriften densamma som från `python -m spectrometer.main`.

`python -m spectrometer.main` startar prompten `spektro>`. `help` listar kommandona, `quit` eller Ctrl+D avslutar, och
ett fel skrivs som en rad `Fel: ...` varefter prompten fortsätter. Sökvägar skrivs med `/`, aldrig `\`.
Utan `source` mäter programmet från kamera 0; utan kamera, skriv `source file <bild>` först.
Programmet minns inget mellan två starter: `dark`, `calibrate`, `response build` och `reference` körs om efter varje
start.

Exempelkörning med bildfilen och kommandofilen `exempel/del1.txt` (Adrians testbild `tests/data/bilder/rand_x12.png`
och punktfilen `exempel/punkter.csv`):

```powershell
Get-Content exempel\del1.txt | python -m spectrometer.main
```

```bash
python -m spectrometer.main < exempel/del1.txt
```

Den skriver `Topp 200 vid pixel 12 (1 bild)`, sedan `Topp 200 vid våglängd (nm) 412 (1 bild)` och `Sparad i
data/ÅÅÅÅMMDD-HHMMSS`: en ny mätmapp under `data/` med `spectrum.csv`, `raw.png` och `settings.json`.
`python -m spectrometer.main <bild>` mäter en bildfil en gång, sparar och ritar spektrumet.

Med kameran på uppställningen skrivs kommandona vid prompten, i den här ordningen: `dark` före `response build` och
`reference`, och `calibrate` före `response build`. Värdena i vinkelparenteser är dina egna: `<x> <y> <bredd> <höjd>`
är ROI:n på uppställningen i pixlar, `<kanal>` den kanal du valde (`gray`, `sum`, `red`, `green` eller `blue`),
`<punktfil>` din punktfil för uppställningen (kolumnerna `pixel`, `wavelength_nm`, `check`) och `<känd fördelning>`
CSV-filen med lampans kända fördelning (`wavelength_nm`, `relative_power_per_nm`). Exponeringen ställs först enligt
Kamera nedan.

```
source camera 0
roi <x> <y> <bredd> <höjd>
channel <kanal>
dark
calibrate <punktfil>
response build <känd fördelning>
response on
frames 16
step
save
reference
mode transmission
step
save
quit
```

## Tester

```
python -m pytest
ruff check .
```

Använd alltid `python -m pytest`, inte `pytest`, så att testerna kör i den aktiverade miljön och hittar
`pyproject.toml`. `tests/test_elias.py` är Elias egna tester (`python -m pytest -q -k elias`): prompten, Ctrl+C,
kameran utan kamera och konstiga bildfiler. Resten i `tests/` är Adrians tester och gör sin egen indata.
`PROTOKOLL-ELIAS.md` är Elias logg med en rad per del (`klar` och `anteckna` i `verktyg-elias.ps1`, på Arch
`verktyg-elias.sh`), och `testprotokoll/` är Adrians. Det testerna inte når (kameran, uppställningen, installationen
på en ren dator) kontrolleras för hand och står i testprotokollet.

Kommandofilerna i `tests/kommandon/` är Adrians regressionstester: `testa_NN.txt` matas till programmet som i
exempelkörningen under Körning, och utskriften ska vara lika `facit_NN.txt`, bortsett från mätmappens namn och
residualer på 1e-10 och mindre. `testa_08b.txt` använder `x12_kand.csv`, en känd fördelning som börjar vid 490 nm, så
att svaret blir detsamma på x64 och ARM.

Frysmappen `testprotokoll/2026-10-19_frys/` är underlaget till Delrapport 2: `pytest.txt`, DR2-tabellen (`protokoll.md`),
kravmatrisen (`kravmatris.md`), bevismapparna och kodbilagan `kod.pdf` (Krav 11: de fem filerna i `spectrometer/`
ur taggen `v1.0.0`, med hashen överst).

Testerna visar att räkningarna stämmer med sina tal. De visar inte att instrumentet mäter rätt: kamerans tal är
relativa counts, aldrig watt eller verkningsgrad, och mjukvarutester bevisar inte att instrumentet mäter rätt
fysikaliskt.

## Förenklingar

Det programmet med flit gör mindre av än rev7, och varför.

| rev7 säger eller antyder | Programmet gör | Varför |
|---|---|---|
| Command- och CommandResult-objekt, argparse per kommando, kommandona `roi set`, `status`, `roi show`, `snapshot save` och `average set`, och `--input` eller `--camera` vid start | Vanliga funktioner och en ordbok `COMMANDS`. Kommandona heter `roi`, `show`, `save` och `frames`, och källan väljs med `source` | Enklare att skriva och läsa, och kraven nås ändå |
| Tillstånd (idle, running, paused), en Application, trådar, `stop` och `view spectrum` | Inga tillstånd och inga trådar. Ctrl+C eller fönstrets kryss stoppar `start` | Live behöver inget mer maskineri |
| Egna klasser och en `core.py` | Inga egna klasser och ingen `core.py`: funktioner i fem filer | Det räcker för kraven |
| Profiler med sparade inställningar | Inga profiler. `dark`, `calibrate`, `response build` och `reference` körs om efter varje start, och mörker, respons och referens sparas inte i mätmappen | Hela bilder som tal i JSON blir enorma, och kalibreringen tar sekunder att köra om med en kommandofil |
| Läsa tillbaka en mätmapp | Mätmappen har bara `spectrum.csv`, `raw.png` och `settings.json` och läses inte tillbaka | Inget krav läser tillbaka |
| Mättnad markeras i masken | `step` varnar vid 255 i råbilden men markerar inte i masken | Varningen räcker för att sänka exponeringen och mäta om |
| Kompatibilitet mellan mätningar | Bara bildstorlek, x-axel och kanal kontrolleras mot mörkret och referensen. Exponering, gain och lampa hålls lika för hand | Programmet kan inte se dem; värdena skrivs under Kamera |
| Rått sensorformat | `raw.png` är den avkodade 8-bitarsbilden, inte kamerans eget råformat | OpenCV ger den avkodade bilden |
| RX18 och absorbans | RX18 saknas. Absorbansen `A = -log10(T)` finns bara som kolumnen `absorbance` i `spectrum.csv` i mode transmission | Det räcker för Krav 22 |
| En gemensam funktion för respons och transmission | `transmission_ratio` är en kopia av `apply_response` med egna namn och fel | Två små funktioner med egna felmeddelanden är lättare att läsa |
| Spridningen (standardavvikelsen) i mätningen | Räknas i `average_spectra` men används inte efter 0.5 | Bara medlet behövs för kraven |
| Kameran på alla system | V4L2 på Linux och DirectShow på Windows; på andra system väljer OpenCV själv. Exponering, gain och vitbalans ställs utanför programmet | Programmet ställer inga reglage; Linux är huvudvägen och Windows fungerar för samma kommandon |
| Gränsen för kontrollfelet (B8) | `calibrate` varnar när kontrollfelet är större än ett lokalt pixelsteg | Planens förslag, inte rev7:s |
| Gränsen för ett misstänkt mörker | `dark` varnar när mörkrets medel är minst hälften av förra bildens medel | Planens förslag, inte rev7:s: då var ljusvägen troligen inte blockerad |

## Kamera

Gäller Linux (Arch) och Windows. Pixelvärdena är counts: relativa tal utan enhet. De visar inte ljusets absoluta styrka eller någon verkningsgrad. Stäng andra program som använder kameran (guvcview, Kamera-appen, webbläsaren) först.

1. **Datorn ser kameran.**
   - Linux: `v4l2-ctl --list-devices`. Kameran har ofta två noder; bara den som listar format under `v4l2-ctl --device=/dev/video0 --list-formats-ext` ger bilder.
   - Windows: `Get-PnpDevice -Class Camera,Image`. Raden för kameran ska ha Status `OK`.
2. **Du vet vilket N som ger bilden.** Linux: N i `/dev/videoN`. Windows: kamerans plats i listan, 0 är den första (en inbyggd kamera tar ofta 0 och USB-kameran blir 1). Prova:

   ```
   python check_install.py --kamera N
   ```

   Den öppnar kamera N och skriver form, dtype, max och medel för tre bilder (`--bilder K` ändrar antalet). `OBS: mörk första bild` betyder att kameran behöver värmas upp, se Öppna punkter.
3. **Lås exponering, gain och vitbalans**, så att två mätningar går att jämföra.
   - Linux (kör före varje mätning; reglagen nollställs när kameran kopplas ur; namnen skiljer mellan kameror, kopiera dem från `v4l2-ctl -d /dev/videoN --list-ctrls`):

     ```bash
     v4l2-ctl -d /dev/videoN --set-ctrl=auto_exposure=1
     v4l2-ctl -d /dev/videoN --set-ctrl=white_balance_automatic=0,gain=0
     v4l2-ctl -d /dev/videoN --get-ctrl=auto_exposure,white_balance_automatic,gain
     ```

     `auto_exposure=1` betyder manuell. `--get-ctrl` ska ge `auto_exposure: 1`, `white_balance_automatic: 0` och `gain: 0`.
   - Windows: drivrutinens egen ruta, som öppnas med `cv2.CAP_PROP_SETTINGS`. Byt 0 mot ditt N, ta bort bocken Auto vid exponering och vitbalans, dra förstärkning (gain) till lägsta, och tryck Enter i PowerShell så att kameran släpps:

     ```powershell
     python -c "import cv2; cap = cv2.VideoCapture(0, cv2.CAP_DSHOW); print(cap.isOpened()); cap.set(cv2.CAP_PROP_SETTINGS, 1); input('Stäng rutan och tryck Enter: '); cap.release()"
     ```
4. **`source camera N`.** Starta programmet (`python -m spectrometer.main`) och skriv `source camera N` med ditt N.
5. **`step` tills toppen ligger mellan 150 och 240 utan `Varning: mättad`.** Ändra bara exponeringen, inte gain. Är toppen under 150: dubbla exponeringen. Står det `Varning: mättad`: halvera den. Kör `step` två gånger efter varje ändring, de första bilderna efter att kameran öppnats kan vara mörkare. Linux: `v4l2-ctl -d /dev/videoN --set-ctrl=exposure_time_absolute=<värde>` i en andra terminal (börja med default från `--list-ctrls`). Windows: avsluta programmet med `quit`, ändra exponeringen i rutan från punkt 3 och starta programmet igen.
6. **Skriv in värdena här och i protokollet.** Fyll i raderna nedan vid kameran, utan enhet, och ta bort den dators rad du inte använder:

   - Linux: kamera N = _, exposure_time_absolute = _, topp i `step` = _
   - Windows: kamera N = _, exponering i drivrutinsrutan = _, topp i `step` = _

   Protokollet (en rad per punkt, i PowerShell efter `. .\verktyg-elias.ps1`, i bash efter `. ./verktyg-elias.sh`):

   ```
   anteckna -Del "0.6.1 del 1" -Vad "Datorn ser kameran, check_install --kamera N" -Not "kamera N"
   anteckna -Del "0.6.1 del 4" -Vad "Exponeringen står i README, toppen 150-240 utan Varning: mättad" -Not "exponering _, topp _"
   ```

## Öppna punkter

- Kamerafelet `camera.open_failed: kunde inte öppna /dev/videoN. Kontrollera med v4l2-ctl --list-devices.` nämner `/dev/video` och `v4l2-ctl` också på Windows. Texten är skriven för Linux och ändras bara tillsammans med Adrians facit.
- Å, ä och ö i sökvägar med OpenCV på Windows: `cv2.imread` kan misslyckas med bildfiler i mappar med å, ä eller ö i namnet, och programmet svarar då att filen inte gick att läsa som bild. Håll projektet och bilderna i en mapp utan å, ä och ö i hela sökvägen. Inte åtgärdat.
- Uppvärmning: den första bilden efter att kameran öppnats kan vara mörk. `step` öppnar kameran vid varje anrop, så det hjälper inte att köra `step` en gång till. Mät med `python check_install.py --kamera N --bilder 5`. Säger den `OBS: mörk första bild`, överväg att läsa bort några bilder i `open_source`, med antalet från en inställning och inget fast tal i koden.
- Kameran är inte provad på uppställningen. Kamerabeviset (0.6.1 del 1 och 4, Krav 13) och fallen A13, A06, A15 och A07 i testprotokollet står som Blockerat tills kameran, lysröret, lampan och filtren finns; då fylls värdena under Kamera, punkt 6, i. Allt annat för 1.0 är gjort.

## Installation

Programmet kräver Python 3.12 (filen `.python-version`). Kommandona körs i projektmappen.

### Windows (huvudväg)

Klona till en kort sökväg som inte ligger i OneDrive eller på Skrivbordet, till exempel `C:\spektro` (se Låsta mappar nedan). Adressen står på GitHub-sidan under knappen Code.

```powershell
git clone ADRESSEN C:\spektro
cd C:\spektro
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python check_install.py
```

Sista raden ska skriva `Installationen stämmer.` Säger `Activate.ps1` att skript inte får köras: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` en gång och öppna ett nytt fönster.

### Windows med uv (alternativ)

```powershell
winget install --id astral-sh.uv
uv python install 3.12
uv venv --seed
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt -r requirements-dev.txt
python check_install.py
```

### Arch

```bash
sudo pacman -S git uv
git clone ADRESSEN ~/spektro
cd ~/spektro
uv python install 3.12
uv venv --seed
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
python check_install.py
```

Klagar `import cv2` på `libGL.so.1`: installera libGL (Arch: `libglvnd`, Ubuntu: `libgl1`, som CI gör).

### Starta utan att aktivera miljön

```powershell
.\.venv\Scripts\python.exe -m spectrometer.main
```

```bash
.venv/bin/python -m spectrometer.main
```

### Låsta mappar (Windows)

- Klona till `C:\spektro`, inte till OneDrive eller Skrivbordet. OneDrive synkar filerna medan programmet skriver dem och kan låsa dem.
- Ger `save` felet `[WinError 5]` (åtkomst nekad) är det oftast antivirus. Undanta mappen (Windows-säkerhet, Virus- och hotskydd, Hantera inställningar, Undantag, Lägg till mapp) eller spara någon annanstans: `save C:/spektro-test`. Adrians testmapp heter redan `C:\spektro-test`.

## Kamera

Programmet ställer inga reglage på kameran. Exponering, gain och vitbalans sätts utanför programmet och ska vara låsta under hela en mätserie, med autoexponering och automatisk vitbalans avstängda. Annars går mätningarna inte att jämföra.

| | Arch-laptop | Windows-desktop | Adrians ARM-laptop |
|---|---|---|---|
| Backend (`source.py`) | V4L2 | DirectShow | DirectShow, x64-Python under emulering |
| Kameranummer N | `v4l2-ctl --list-devices`: N i `/dev/videoN` | prova 0, 1, 2 med `python check_install.py --kamera N` | som Windows-desktop |
| Låsrader | `v4l2-ctl --set-ctrl` (nedan) | drivrutinsrutan (nedan) | drivrutinsrutan |
| Exponering så att toppen blir 150 till 240 | fylls i på riggen | fylls i på riggen | fylls i på riggen |
| Första bilden efter öppning | kan vara mörk, inte åtgärdat | som Arch | som Arch |
| Provad med riktig kamera | ja (datum fylls i) | nej | nej |

Programmet öppnar kameran vid varje `step`, `dark` och `reference`. Att köra `step` en gång till hjälper alltså inte mot en mörk första bild; titta på `Topp`-raden och mät om.

### Arch (V4L2)

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-ctrls
v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1
v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute=200
v4l2-ctl -d /dev/video0 --set-ctrl=gain=0
v4l2-ctl -d /dev/video0 --set-ctrl=white_balance_automatic=0
```

Reglagens namn och värden skiljer mellan kameror; `--list-ctrls` visar vad just din har. Hos de flesta USB-kameror betyder `auto_exposure=1` manuell exponering och 3 automatisk. Värdet 200 är ett exempel: rätt värde är det som ger toppen 150 till 240 utan raden `Varning: mättad`. Exponeringens enhet bekräftas på riggen.

Provad på Arch: ÅÅÅÅ-MM-DD (fyll i datum och klistra in utskriften från `--list-ctrls` här när du kört den på riggen).

### Windows (DirectShow): inte provad med riktig kamera

Kameran är inte provad på Windows. Gör så här och skriv in resultatet i tabellen och här när du provat:

1. Öppna Inställningar, Sekretess och säkerhet (Integritet i äldre Windows), Kamera, och slå på tillåt skrivbordsappar. Namnen skiljer något mellan Windows-versioner.
2. Stäng Teams, Kamera-appen och allt annat som kan hålla kameran. Bara ett program får ha den.
3. `python check_install.py --kamera 0` (prova 1 och 2 om 0 inte går).
4. Exponering och gain ställs i drivrutinsrutan (antaget, inte provat):

```powershell
python -c "import cv2; c = cv2.VideoCapture(0, cv2.CAP_DSHOW); c.set(cv2.CAP_PROP_SETTINGS, 1); input('Tryck Enter när rutan är stängd')"
```

Felraden `camera.open_failed: kunde inte öppna …` säger vad du ska prova på just ditt system: på Windows andra program som håller kameran och sekretessinställningen för kameran, på Linux `/dev/video0` och `v4l2-ctl`.

### Kameraprotokoll per mätdag

Programmet sparar inte kamerans reglage. Spara dem själv i mätserien:

- Arch: `v4l2-ctl -d /dev/video0 --all > data/led_rod/kamera.txt`
- Windows: en skärmbild av drivrutinsrutan i samma mapp.

Skriv exponering, gain, vitbalans och upplösning i en rad i en textfil bredvid.

## Om kameraläsningen hänger

Kameraläsningen (`cap.read()`) har ingen tidsgräns och kan stå still vid ett USB-fel (antaget på Windows, inte sett). Gör så här, i ordning, tills det släpper:

1. Ctrl+C i terminalen.
2. Stäng fönstret med kurvan.
3. Stäng terminalen. Eller: `taskkill /F /IM python.exe` (Windows, stänger alla Python-program) eller `pkill -f spectrometer` (Arch).
4. Dra ut USB-kabeln och sätt i den igen.
5. Starta programmet. Uppsättningen (källa, ROI, mörker, kalibrering, referens) är borta och görs om från början.

## Vad som är provat

| Dator | Python 3.12 | pytest | facit | Kamera (live) |
|---|---|---|---|---|
| Arch-laptop (primär) | ej bekräftat | ej bekräftat | ej bekräftat | ja, V4L2 (datum fylls i) |
| Windows x64 (Elias skrivbordsdator) | ja (`py -3.12 -m venv` och pip) | ja | ej bekräftat | nej, inte provad |
| Windows 11 ARM (Adrian, x64-Python under emulering) | ja | ja | ja, men `facit_08b` gav `2 av 3` innan `x12_kand.csv` | nej, oprövad under emulering |

`ej bekräftat` betyder att ingen har skrivit upp att det är kört, inte att det är fel. Den som kör något fyller i datum. Uppgifterna är sammanställda ur projektets anteckningar 2026-10-19.

## Öppna punkter

Frågor som ingen har svarat på. README påstår inget om dem.

| ID | Fråga | Status | Avgörs av | Senast kontrollerat |
|---|---|---|---|---|
| B5 | Vilken lampa med känd fördelning (Krav 14) och vilken linjekälla (Krav 16)? | öppen, meddelande till handledaren skrivet, svar okänt | handledaren (Chih-Wei Hsu) och gruppen | 2026-10-19 |
| B6 | När är uppställningen klar, och ligger spektrumbandet vågrätt eller lodrätt? | öppen | Oscar | 2026-10-19 |
| B8 | Toleranser för kalibrering, kontrollfel och mätvariation | öppen, beror på B5 och B6 | Adrian och Elias föreslår | 2026-10-19 |
| B9 | Kursens regler för AI-hjälp | öppen, inte kontrollerad | kursansvarig (Urban Forsberg) | 2026-10-19 |
| B11 | Är en sparad 8-bitars webbkamerabild "rådata" enligt Krav 12? | öppen, fråga handledaren | handledaren | 2026-10-19 |

Lampa och datakälla för känd fördelning skrivs här när B5 är avgjord. Uppdatera raden och datumet vid varje kontroll.

## Så jobbar vi

1. Koden ligger på GitHub. `adrianfemboygaming` är grenen koden utvecklas på; Adrians testgren heter `tester` och där ligger `testprotokoll/`.
2. Elias äger `spectrometer/`, `tests/test_elias.py`, `tests/test_main.py`, `check_install.py` och `spektro.py`.
3. Adrian äger `tests/test_calc.py`, `tests/test_files.py`, `tests/kommandon/` (facit) och `testprotokoll/`. Rör inte den andres filer utan att säga till.
4. Facit är Adrians kontrakt. Utskriften ändras bara med ett eget commit som säger vilka rader och varför.
5. Före varje commit: `python -m ruff check .` och `python -m pytest -q`. CI kör samma på Linux och Windows.
6. Betataggar som `v0.6.2beta` sätts sist i en del, när allt är grönt. `v1.0.0` är frysen för delrapport 2.
7. `klar` och `anteckna` i `verktyg-elias.ps1` skriver en rad i `PROTOKOLL-ELIAS.md`: `klar` när en del är färdig, `anteckna` för en notering på vägen.
8. Commit-meddelanden börjar med versionen: `1.0.14 quality.py: mättnad`.
9. Hittar Adrian ett avvikande resultat öppnar han en Issue med kommandofil, utskrift och dator. Elias svarar i Issuen och stänger den i commit-meddelandet (`Closes #N`).
10. Är något oklart i README eller bruksanvisningen skriver man det i en Issue. Den som lärt sig något rättar texten.

## Snabbstart

Fyra kommandon på en testbild, utan kamera. Aktivera miljön, starta programmet och skriv sedan raderna efter `spektro>`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m spectrometer.main
```

```
spektro> source file tests/data/bilder/rand_x12.png
source file tests/data/bilder/rand_x12.png
spektro> step
Topp 200 vid pixel 12 (1 bild)
spektro> save
Sparad i data/20261020-102233
spektro> quit
Avslutar.
```

Mappnamnet i `Sparad i` är tid och datum för din körning. Fick du `Topp 200 vid pixel 12 (1 bild)` fungerar installationen. Det visar bara att räkningen stämmer på en testbild, inte att kameran och uppställningen mäter rätt.

## Kommandon

Tabellen nedan fylls av `python tools/gen_kommandon.py` ur koden. `python tools/gen_kommandon.py --check` säger om den är aktuell. Kör skriptet när du lagt till eller ändrat ett kommando; CI kontrollerar det inte. Hela referensen finns i `docs/kommandon.md`; `help KOMMANDO` visar syntaxen i programmet.

<!-- KOMMANDON START -->
| kommando | syntax | vad |
|---|---|---|
| help | help [KOMMANDO] | Kommandot help [KOMMANDO]: en rad per kommando i registret, eller raden och syntaxen för ett kommando. |
| quit | quit | Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True); frågar först om en osparad mätning. |
| show | show | Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns. |
| status | status | Kommandot status: mörker, kalibrering, respons, referens och läge på en rad, sedan nästa steg i kedjan. |
| version | version | Kommandot version: programmet, Python, biblioteken, git och operativsystemet på en rad. |
| source | source file PATH eller source camera N | Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden. |
| roi | roi X Y W H eller roi full | Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden ger fel och den gamla står kvar. |
| channel | channel gray, sum, red, green eller blue | Kommandot channel NAMN: färgkanal ur calc.CHANNELS. |
| axis | axis horizontal eller axis vertical | Kommandot axis RIKTNING: riktning ur session.AXES. |
| frames | frames N | Kommandot frames N: antalet bilder per mätning, från 1 till registry.MAX_FRAMES (1000). |
| info | info | Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen. |
| cameras | cameras | Kommandot cameras: provar kameranummer 0 till 4 med source.probe och skriver en rad per nummer. Källan ändras inte. |
| snap | snap | Kommandot snap [N]: läser N bilder ur källan och sparar dem som PNG; state ändras inte. |
| image | image | Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger. |
| step | step | Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1,05. |
| save | save [DIR] | Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir. |
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
| rigg | rigg, rigg PATH eller rigg off | Kommandot rigg [PATH\|off]: läser rigg.json (fälten i docs/rigg.md) till state["rigg"]; save skriver den. DOK-31. |
<!-- SLUT -->

## Så sparas en mätning

`save` skriver en mapp med tid och datum, till exempel `data/20261020-102233`. Med `save DIR` blir `DIR` föräldramappen. Skriv sökvägar med snedstreck, även på Windows.

| Fil | Innehåll |
|---|---|
| `spectrum.csv` | spektrumet, en rad per position (kolumnerna nedan) |
| `raw.png` | den sista bilden som lästes, avkodad till 8 bitar, före mörkeravdrag. Inte sensorns rådata |
| `settings.json` | inställningarna som gällde: `source`, `roi`, `axis`, `channel`, `output_dir`, `frames`, `min_response`, `min_reference`, `coefficients`, `dark`, `use_response`, `mode` |

Kolumnerna i `spectrum.csv`:

| Kolumn | Enhet | Exempel |
|---|---|---|
| `x_px` eller `x_nm` | pixel, eller nm när en kalibrering finns | `12` |
| `value` | counts, relativt. Det korrigerade värdet (efter mörker, ev. respons och transmission), inte råa counts. Tom där `valid` är false | `200` |
| `valid` | `true` eller `false` | `true` |
| `absorbance` | bara i `mode transmission`: -log10 av transmissionen, tom där den saknas | |

Exempelrad från testbilden: `12,200,true`. Alla tal är kamerans relativa värden, aldrig watt eller verkningsgrad.

### Öppna i Excel eller Calc

Dubbelklicka inte på filen. Svenskt Excel läser `1.5` som ett datum. Importera i stället:

- Excel: Data, Från text/CSV, avgränsare Komma, och språk Engelska (USA) så att punkt blir decimaltecken.
- Calc: Arkiv, Öppna, välj filen; i importrutan avgränsare Komma, teckenkodning UTF-8, språk Engelska (USA).

### Serier och USB-minne

Gör en mapp per diod och låt programmet lägga en tidsstämplad undermapp per mätning: `save data/led_rod_20mA` ger `data/led_rod_20mA/ÅÅÅÅMMDD-HHMMSS`.

På ett USB-minne: `save E:/mat` (Windows, med snedstreck) eller `save /run/media/ANVÄNDARE/NAMN/mat` (Arch). Kontrollera att mappen syns i Utforskaren eller med `ls`, och mata ut minnet innan du drar ut det. Prova en gång på båda datorerna före demon.

## Mätkedjan i ordning

Programmet minns inget mellan två starter. Ordningen är:

1. `source`, sedan `roi`, `channel`, `axis`, `frames`.
2. `dark` (ljusvägen blockerad).
3. `calibrate PUNKTFIL`.
4. Valfritt: `response build KANDFIL` och `response on`.
5. Direkt mätning: `step` och `save`. Transmission: `reference` (utan prov), `mode transmission`, `step` och `save`.

| Kommando | Kräver | Tömmer eller glömmer |
|---|---|---|
| `source` | | senaste bilden och mätningen. Mörker, kalibrering, respons och referens finns kvar |
| `roi`, `channel` | | mätningen och **responsen** (`Responsen glömd. Kör response build igen.`). Referensen: ändras kanalen, eller `roi`s läge i sidled eller bredd, ger `step` i transmission fel tills `reference` körs om. Ändras bara höjden märker programmet inget: kör `reference` om ändå |
| `axis`, `frames` | | mätningen |
| `calibrate` | | mätningen. Responsen och referensen finns kvar men gäller den gamla kalibreringen: kör om dem om kalibreringen ändrades |
| `dark` | | mätningen och **referensen** (`referensen togs bort: kör reference igen`) |
| `reference` | `dark` | mätningen |
| `response build` | `dark`, `calibrate` | mätningen |
| `response on`, `response off` | `response build` | mätningen |
| `mode transmission` | `reference` | mätningen |

## Vilken kanal?

`channel` väljer vilken färg som blir spektrumet. Alla mätningar i en serie, och referensen, ska använda samma kanal.

| Kanal | Vad | Topp | Mättnad |
|---|---|---|---|
| `gray` (förval) | vägd summa: 0,299 röd + 0,587 grön + 0,114 blå | fylls i på riggen | fylls i på riggen |
| `sum` | röd + grön + blå, kan bli över 255 | fylls i på riggen | fylls i på riggen |
| `red`, `green`, `blue` | en färg | fylls i på riggen | fylls i på riggen |

Webbkamerans Bayer-filter ger olika känslighet per färg. Antaget, inte mätt: `sum` mättar tidigast och `green` har flest pixlar. Tabellen fylls i genom att mäta samma lampa i varje kanal.

## Kalibreringsfilen: kontrollpunkten

Punktfilen har rubriken `pixel,wavelength_nm,check`. Rader med `check` 0 anpassar linjen, rader med 1 kontrollerar den. Kontrollraden ska ligga mitt i intervallet, för då prövas interpolation. Finns en linje utanför de anpassade tas den som en andra kontroll, för att se vad extrapolering kostar. Fyra anpassningspunkter och en kontrollpunkt är gruppens minimum; programmet godtar två punkter för grad 1.

## Fönstret

`start` visar spektrumet live. Fönstret har matplotlibs vanliga verktygsrad och tangenter (inte provade i vårt program på riggen):

- `q` stänger fönstret, och live stoppar som med krysset.
- `s` öppnar dialogen för att spara bilden som PNG.
- `l` växlar logaritmisk y-axel, `g` rutnät, `f` helskärm.
- Musen visar x och y nere till höger.

Fönstret kan ligga bakom terminalen: Alt+Tab. För Ctrl+C: klicka först i terminalen. `save` direkt efter `start` sparar den sista live-kurvan. `step` ritar inget fönster, bara `start` gör det.

## Språk

Kommandon och flaggor är på engelska, texten till användaren är på svenska och felkoder är på engelska (`input.invalid_argument`). `show` skriver inställningarna med samma nycklar som `settings.json` (`roi`, `axis`, `channel`, `output_dir`, `frames`); bara `source` heter `källa` i `show`.

## Kända egenheter (gäller 1.0.41)

- Ctrl+D avslutar på Arch. På Windows är det Ctrl+Z och Enter, fast programmet säger Ctrl+D.
- Felmeddelandet om kameran nämner `/dev/video` även på Windows.
- `help` skrivs utan justering i kolumner.
- `step` ritar inget fönster. Bara `start` gör det.
- Skriv sökvägar med snedstreck. Ett bakslag (`\`) tas bort av kommandoläsaren: `save C:\mat` blir `C:mat`.
- Programmet kontrollerar inte att exponering och gain är desamma mellan `dark` och mätningen. Det gör du.

## Tester och vad de visar

```powershell
python -m pytest -q
python -m pytest -q -k facit
python -m pytest -v -rA
```

`-k ORD` kör bara tester vars namn innehåller ORD. `-v -rA` listar varje test med resultat. Vad filerna gör:

| Fil | Vad den prövar |
|---|---|
| `tests/test_calc.py` | räkneexemplen RX01, RX02 och RX05 i `calc` (Adrian) |
| `tests/test_files.py` | att `save_measurement` skriver rätt `spectrum.csv` (Adrian) |
| `tests/test_source.py` | att en bildfil läses oförändrad |
| `tests/test_main.py` | att `measure` ger rätt spektrum utan fönster |
| `tests/test_elias.py` | det Adrians tester inte täcker: prompten, Ctrl+C, kameran (låtsaskamera), konstiga bildfiler, ROI och frames |
| `tests/test_facit.py` | kör Adrians kommandofiler `tests/kommandon/testa_NN.txt` genom det riktiga programmet och jämför med `facit_NN.txt` |
| `tests/test_architecture.py` | vem som får importera vem, att bara `out.py` skriver ut, att varje kommandomodul går att ta bort |
| `tests/test_help.py` | kommandoregistret, `help KOMMANDO` och `tools/gen_kommandon.py` |
| `tests/test_show.py` | att `show` och ekot skrivs på vanlig svenska |
| `tests/test_readme.py` | att Snabbstart ger `Topp 200 vid pixel 12 (1 bild)` |

Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt. Att uppställningen, kameran och kalibreringen ger riktiga spektrum visar bara mätningar på riggen.

## Dokument

- `docs/bruksanvisning.md`: bruksanvisningen, version 1, för en läsare som inte kan programmet. Inte provad på uppställningen än.
- `docs/snabbkort.md`: ett A4 med mätkedjan i 12 rader och vad du ska se på varje rad.
- `docs/kommandon.md`: kommandoreferensen, skapad av `python tools/gen_kommandon.py`.

## Demo

`demo/` har kommandofilerna för demon (`1_forbered.txt`, `2_kalibrera.txt`, `3_mata.txt`) och `reserv.txt`, som kör hela kedjan på sparade bilder om kameran sviker. Läs `demo/README.md` först. Bilderna och punktfilerna tas på riggen och finns inte än. `tests/test_demo.py` kör reservkedjan på påhittade bilder.

### Demo-dagen

`demo/manus.md` (60 minuter med roller), `demo/checklista.md` (datum och tre rutor) och `demo/fragor.md` (förväntade frågor). Tal som saknas i dem fylls i från riktiga körningar på uppställningen.

## Begränsningar

Samma rader som `help limits` skriver i programmet (`tests/test_demoflode.py` kontrollerar att de är lika):

- Intensiteten är relativ: kameran ger counts, inte watt, lumen eller verkningsgrad.
- 8 bitar: varje pixel är 0–255; vid 255 är den mättad och toppen blir för låg (step varnar).
- Fönstret är 366–766 nm med KO-kalibreringen: utanför finns ingen kalibrerad våglängd.
- Upplösningen är FWHM för en smal linje (laser eller lysrörets 576,96 och 579,07 nm); calibrate save skriver den.
- Färg och färgtemperatur kräver response on; färgtemperaturen gäller bara nära svartkroppskurvan.
- Bandgapet är brantaste lutningen extrapolerad till A = 0; osäkerheten är bara ±0,5 pixelsteg.
- Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.
