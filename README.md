# Efficient light sources: spectrometer

A program that turns a webcam image (or an image file) of a spectrum into a spectrum curve, in pixels or in nm after
calibration. Course TFYY51, group GRYb1.

## Install and start

Python 3.12. In the project folder:

```
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt     (Windows: .venv\Scripts\python.exe)
.venv/bin/python check_install.py                       (Windows: .venv\Scripts\python.exe)
```

Start with `python spektro.py` (it builds `.venv` the first time). On Windows you can double-click `Spektro.pyw`, on
Arch `bash arch_start.bash` does the setup. The window needs Tk (Arch: `sudo pacman -S tk`, Debian/Ubuntu:
`sudo apt install python3-tk`), without it you get the terminal. `help` lists the commands, `quit` exits.

## Example measurement

```
spektro> source camera 0
spektro> roi X Y W H
spektro> dark
spektro> calibrate POINTSFILE
spektro> step
spektro> save
```

`dark` is taken with the light path blocked. `POINTSFILE` is a CSV with known lines (see `examples/calibration/`). `save`
writes a folder under `data/` named after the date and time, with `spectrum.csv`, `raw.png`, `settings.json` and
`spectrum.png`. Without a camera you can try a test image:

```
spektro> source file tests/data/images/rand_x12.png
spektro> step
Peak 200 at pixel 12 (1 frame)
```

More in `docs/user-guide.md`. The example files are in `examples/`.

## Limitations

- The intensity is relative: the camera gives counts, not watts, lumens or efficiency.
- The tests show that the computation is right, not that the instrument measures correctly.
