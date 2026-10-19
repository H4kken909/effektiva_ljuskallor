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
3. `git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git`
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
2. `git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git`
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

`python -m spectrometer.main` startar prompten `spektro>`. `help` listar kommandona, `quit` eller Ctrl+D avslutar, och
ett fel skrivs som en rad `Fel: ...` varefter prompten fortsätter. Sökvägar skrivs med `/`, aldrig `\`.
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
