"""Spårbarheten: programversion, tid, git, bibliotek, profiler och settings_id till settings.json och kommandot version.

Inget här får stoppa en mätning: saknas git (ZIP-nedladdning, git inte installerat) blir git_commit och git_dirty None.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np

from spectrometer import __version__, files

ROOT = Path(__file__).resolve().parents[1]  # mappen med spectrometer/ och .git
NOT_IN_ID = ("note", "measured_at", "annotations", "program_version", "git_commit", "git_dirty", "libraries")


def _git(*args):
    """Kör git i programmets mapp och ger utskriften. OSError utan git, SubprocessError vid fel eller tidsgräns."""
    done = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        check=True,
    )
    return done.stdout


def git_state():
    """(commit, dirty): kort commit och True om något är ändrat sedan den; (None, None) om git inte svarar."""
    try:
        commit = _git("rev-parse", "--short", "HEAD").strip()
        dirty = _git("status", "--porcelain") != ""
    except (OSError, subprocess.SubprocessError):
        return None, None
    return commit, dirty


def libraries():
    """Python och biblioteken som gav mätningen, som text (matplotlib None om den inte går att läsa)."""
    try:
        matplotlib = metadata.version("matplotlib")
    except metadata.PackageNotFoundError:
        matplotlib = None
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "opencv": files.opencv_version(),
        "matplotlib": matplotlib,
    }


def profiles(state):
    """Mörker, respons och referens i några tal (None där den saknas), till settings.json."""
    result = {"dark": None, "response": None, "reference": None}
    if state["dark"] is not None:
        result["dark"] = {"frames": state["dark_frames"], "mean": round(float(np.mean(state["dark"])), 3)}
    if state["response"] is not None:
        response = state["response"]
        result["response"] = {
            "valid_positions": int(np.count_nonzero(np.isfinite(response["values"]))),
            "frames": response.get("frames"),
            "known_file": response.get("known_file"),
        }
    if state["reference"] is not None:
        reference = state["reference"]
        result["reference"] = {
            "frames": reference.get("frames"),
            "channel": reference["channel"],
            "x_first": float(reference["x"][0]),
            "x_last": float(reference["x"][-1]),
        }
    return result


def settings_id(saved):
    """De 12 första hex-tecknen av SHA-256 över saved med sorterade nycklar, utan nycklarna i NOT_IN_ID."""
    kept = {key: value for key, value in saved.items() if key not in NOT_IN_ID}
    text = json.dumps(kept, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def with_metadata(state, saved):
    """En ny ordbok: saved med programversion, tid, git, bibliotek, profiler och settings_id före "coefficients".

    Före coefficients, så att slutet av settings.json (coefficients, dark, use_response, mode) är som förut.
    """
    commit, dirty = git_state()
    extra = {
        "program_version": __version__,
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": commit,
        "git_dirty": dirty,
        "libraries": libraries(),
        "profiles": profiles(state),
        "extraction": {"rows": state["rows"], "background": state["background"]},
    }
    extra["settings_id"] = settings_id(saved | extra)
    keys = list(saved)
    cut = keys.index("coefficients")
    return {key: saved[key] for key in keys[:cut]} | extra | {key: saved[key] for key in keys[cut:]}


def version_line():
    """Raden som kommandot version skriver: programmet, Python, biblioteken, git och operativsystemet."""
    libs = libraries()
    commit, dirty = git_state()
    git = "git okänd" if commit is None else f"git {commit}" + (" (ändrad)" if dirty else "")
    return (
        f"spektro {__version__}, Python {libs['python']} ({platform.machine()}), numpy {libs['numpy']}, "
        f"opencv {libs['opencv']}, matplotlib {libs['matplotlib']}, {git}, {platform.system()} {platform.release()}"
    )


def put_before(saved, key, value):
    """En ny ordbok: saved med key: value just före coefficients, så att slutet av settings.json är som förut."""
    keys = [k for k in saved if k != key]
    cut = keys.index("coefficients")
    return {k: saved[k] for k in keys[:cut]} | {key: value} | {k: saved[k] for k in keys[cut:]}
