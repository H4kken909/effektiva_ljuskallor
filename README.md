Windows (PowerShell):
1. winget install --id Git.Git -e
2. winget install --id astral-sh.uv -e
3. git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git
4. cd effektiva_ljuskallor
5. git switch adrianfemboygaming
6. uv python install 3.12
7. uv venv --seed
8. .venv\Scripts\Activate.ps1 (första gången: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
9. uv pip install -r requirements.txt -r requirements-dev.txt
10. python check_install.py

Arch Linux (bash):
1. sudo pacman -S --needed git uv github-cli base-devel psmisc v4l-utils guvcview
2. git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git
3. cd effektiva_ljuskallor
4. git switch adrianfemboygaming
5. uv python install 3.12
6. uv venv --seed
7. source .venv/bin/activate
8. uv pip install -r requirements.txt -r requirements-dev.txt
9. python check_install.py

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


# Effektiva ljuskällor – spectrometer

A small Python program that turns a webcam image (or an image file) of a spectrum into a calibrated spectral curve. Built for the course TFYY51 at Linköping University (project group GRYb1), software part of Delrapport 2.

The program is a package, `spectrometer`, with five files:

| File | Responsibility |
|---|---|
| `calc.py` | All calculations (NumPy only) |
| `source.py` | Reads images from a file or the camera |
| `plot.py` | Draws the spectrum |
| `files.py` | Writes the measurement folder |
| `main.py` | Command loop; the only file that imports the other four |

## Installation on Windows (PowerShell)

Works on Windows 10 and 11, on both Intel/AMD and ARM (for example Snapdragon). Open PowerShell (Windows key, type `PowerShell`, Enter) and run each block in order.

1. Install the tools:

   ```powershell
   winget install --id Git.Git -e
   winget install --id GitHub.cli -e
   winget install --id astral-sh.uv -e
   winget install --id Microsoft.VisualStudioCode -e
   ```

2. Close PowerShell and open a new window. Check that all three print a version number:

   ```powershell
   git --version
   gh --version
   uv --version
   ```

3. Log in to GitHub. Answer: `GitHub.com`, `HTTPS`, `Yes`, `Login with a web browser`:

   ```powershell
   gh auth login
   gh auth status
   ```

4. Clone the repository into a folder without spaces:

   ```powershell
   cd C:\
   git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git spektro-test
   cd C:\spektro-test
   ```

5. Create the virtual environment with **x64** Python 3.12. On Windows ARM this x64 Python runs through Windows' built-in emulation. It is required there, because `opencv-python` publishes no Windows ARM64 package, and pip would otherwise try to compile OpenCV and fail with `Unknown compiler(s)`. On Intel/AMD it is the normal Python.

   ```powershell
   uv python install cpython-3.12-windows-x86_64-none
   uv venv --seed --python cpython-3.12-windows-x86_64-none
   ```

6. Allow PowerShell to run the activation script (once per user; answer `Y`), then activate:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   .\.venv\Scripts\Activate.ps1
   ```

   The prompt now starts with `(.venv)`. Check that the right Python is used. The output must be `win-amd64 C:\spektro-test\.venv\Scripts\python.exe`:

   ```powershell
   python -c "import sys, sysconfig; print(sysconfig.get_platform(), sys.executable)"
   ```

7. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt -r requirements-dev.txt
   ```

## Every new terminal

```powershell
cd C:\spektro-test
.\.venv\Scripts\Activate.ps1
```

## Running

```powershell
python -m spectrometer.main tests/data/bilder/rand_x12.png
```

Paths given to the program are written with `/`, never `\`.

## Testing

```powershell
python -m pytest
ruff check .
```

Always use `python -m pytest`, not `pytest`, so the tests use the activated environment and find `pyproject.toml`.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `The module '..venv' could not be loaded` | Activation line mistyped | Type exactly `.\.venv\Scripts\Activate.ps1` |
| `running scripts is disabled on this system` | PowerShell blocks scripts | Step 6, `Set-ExecutionPolicy` |
| `Unknown compiler(s)` while installing `opencv-python` | ARM64 Python in use | Delete `.venv` (`Remove-Item -Recurse -Force .venv`) and redo step 5 |
| `No module named matplotlib` | Environment not activated, or step 7 failed | Activate, redo step 7 |
| `Repository not found` when cloning | GitHub invitation not accepted, or wrong account | Accept the invitation, check `gh auth status` |

## Installation on Linux (Arch)

```bash
sudo pacman -S --needed git uv tk base-devel unzip psmisc v4l-utils guvcview
git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git
cd effektiva_ljuskallor
uv python install 3.12
uv venv --seed
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m spectrometer.main
```

`tk` is needed for Matplotlib windows, `v4l-utils` for `v4l2-ctl` (camera settings). The camera works only on Linux.

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
- B8: kontrollfelet får vara högst ett lokalt pixelsteg. calibrate varnar när det är större. Gränsen är planens förslag, inte rev7:s.
- dark varnar när mörkrets medel är minst hälften av förra bildens medel: då var ljusvägen troligen inte blockerad. Gränsen är planens förslag, inte rev7:s.
