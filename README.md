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
