# Spektrometern

Ett litet Python-program som gör om en bild av ett spektrum, från en webbkamera eller en bildfil, till en kalibrerad spektralkurva. Det är programvaran i Delrapport 2 i kursen TFYY51 (grupp GRYb1).

## Installation

Kommandona är skrivna för bash på Arch Linux. Numren i parentes är bitarna i planen.

1. Uppdatera systemet och installera programmen (0.0.1). VS Code installeras från AUR som `visual-studio-code-bin`, med tilläggen Python, Pylance och Ruff.

   ```bash
   sudo pacman -S --needed git uv github-cli base-devel psmisc v4l-utils guvcview
   ```

2. Klona repot (0.0.2).

   ```bash
   git clone https://github.com/eliasholmberg05/effektiva_ljuskallor.git
   ```

3. Gå in i projektmappen (0.0.2).

   ```bash
   cd effektiva_ljuskallor
   ```

4. Byt till grenen (0.0.2).

   ```bash
   git switch adrianfemboygaming
   ```

5. Installera Python 3.12 (0.0.3). Versionen är låst i `.python-version`.

   ```bash
   uv python install 3.12
   ```

6. Skapa den virtuella miljön `.venv` (0.0.3).

   ```bash
   uv venv --seed
   ```

7. Aktivera miljön. Gör det i varje ny terminal (0.0.3).

   ```bash
   source .venv/bin/activate
   ```

8. Installera biblioteken med exakt de versioner som står i filerna (0.0.4).

   ```bash
   uv pip install -r requirements.txt -r requirements-dev.txt
   ```

Kontroll (0.0.5 till 0.0.8): paketet `spectrometer` och mappen `tests/` finns, och `python -m pytest` säger `no tests ran` och `ruff check .` säger `All checks passed!`.

## Körning

## Tester

## Kamera

## Förenklingar

## Öppna punkter
