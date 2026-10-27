import json
import os
import sys
from pathlib import Path

from spectrometer.visual import theme

FIRST = {"camera": False, "roi": False, "spectrum": False, "panel": False, "rail": True, "status": True,
         "glow": "on", "camera_view": "crop"}
CHOICES = {"glow": theme.GLOW_LEVELS, "camera_view": ("crop", "full")}


def folder():
    if os.environ.get("SPEKTRO_CONFIG"):
        return Path(os.environ["SPEKTRO_CONFIG"])
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / "spektro"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "spektro"


def log_path():
    return folder() / "spektro.log"


def load():
    values = dict(FIRST)
    try:
        saved = json.loads((folder() / "view.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return values, True
    for key in FIRST:
        if key in saved and saved[key] in CHOICES.get(key, (True, False)):
            values[key] = saved[key]
    return values, False


def pick(view):
    return {key: view[key] for key in FIRST if key in view}


def save(view):
    folder().mkdir(parents=True, exist_ok=True)
    (folder() / "view.json").write_text(json.dumps(pick(view), indent=1) + "\n", encoding="utf-8")
