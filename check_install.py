import importlib.metadata
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
errors = 0


def report(level, text):
    global errors
    print(level, text)
    if level == "ERROR":
        errors += 1


if len(sys.argv) > 2 and sys.argv[1] == "--camera":
    import cv2

    cap = cv2.VideoCapture(int(sys.argv[2]), cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2)
    if not cap.isOpened():
        report("ERROR", "could not open the camera, close other programs that use it or try another number")
        sys.exit(1)
    for number in range(1, 4):
        ok, image = cap.read()
        if not ok:
            report("ERROR", f"frame {number} could not be read")
            break
        report("OK", f"frame {number}: {image.shape[1]} x {image.shape[0]}")
    cap.release()
    sys.exit(errors > 0)

report("OK", f"Python {sys.version.split()[0]}")
if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    report("ERROR", "not running in .venv, activate it and run again")

for row in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
    if not row.strip() or row.startswith("#"):
        continue
    name = row.split("==")[0]
    try:
        report("OK", f"{name} {importlib.metadata.version(name)}")
    except importlib.metadata.PackageNotFoundError:
        report("ERROR", f"{name} is missing, run: pip install -r requirements.txt")

try:
    import tkinter

    tkinter.Tk().destroy()
    report("OK", "tkinter works")
except ImportError:
    report("ERROR", "tkinter is missing (Arch: sudo pacman -S tk, Debian/Ubuntu: sudo apt install python3-tk)")
except tkinter.TclError:
    report("WARNING", "tkinter cannot open a window here (fine over SSH)")

if errors:
    print(f"{errors} error(s), fix them and run again")
    sys.exit(1)
print("The installation is right.")
