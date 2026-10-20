"""response save och response load: responsen som en .npz-fil, med det den gjordes med (roi, kanal, axis, kalibrering)."""

import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np

from spectrometer import out, registry, session

NEEDED = ("x", "values", "roi", "channel", "axis")  # det en responsfil måste ha


def _roi_text(roi):
    """ROI:n som i show: hela bilden, eller x y bredd höjd."""
    return "hela bilden" if roi is None else " ".join(str(v) for v in roi)


def _empty_if_none(value, dtype):
    """value som array, eller en tom array när value är None (en .npz kan inte spara None utan pickle)."""
    return np.array([] if value is None else value, dtype=dtype)


@registry.command("response save", "FIL.npz: spara responsen med roi, kanal, axis och kalibrering (skriver aldrig över)",
                  "response save FIL.npz")
def cmd_response_save(state, args):
    """Kommandot response save FIL.npz: x, values, roi, channel, axis, coefficients och pixel_range med np.savez.

    Fel: ValueError med input.missing_data utan respons, input.invalid_argument om FIL redan finns; OSError om den
    inte går att skriva.
    """
    registry.need(args, ("FIL",), "response save")
    response = state["response"]
    if response is None:
        raise ValueError("input.missing_data: ingen respons, kör response build först")
    cfg = state["settings"]
    taken = state["taken"].get("response")
    arrays = {
        "x": response["x"],
        "values": response["values"],
        "roi": _empty_if_none(cfg["roi"], np.int64),  # tom: hela bilden
        "channel": np.array(cfg["channel"]),
        "axis": np.array(cfg["axis"]),
        "coefficients": _empty_if_none(state["coefficients"], np.float64),
        "pixel_range": _empty_if_none(state["pixel_range"], np.float64),
        "frames": np.array(response.get("frames") or 0),
        "known_file": np.array(response.get("known_file") or ""),
        "taken": np.array(taken.isoformat(timespec="seconds") if taken else ""),
    }
    try:
        f = open(args[0], "xb")  # "x": bara en ny fil; en öppen fil gör att np.savez inte lägger till .npz själv
    except FileExistsError as error:
        raise ValueError(f"input.invalid_argument: {args[0]} finns redan, response save skriver inte över") from error
    with f:
        np.savez(f, **arrays)
    out.say(f"respons: sparad i {args[0]}")


def _load(path):
    """Arrayerna i en .npz från response save, lästa utan pickle (allow_pickle=False: filen kan inte köra kod).

    Fel: ValueError med input.invalid_argument om filen inte är en .npz med NEEDED; OSError om den inte går att läsa.
    """
    wrong = f"input.invalid_argument: {Path(path).name} är ingen responsfil från response save"
    try:
        with np.load(path, allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files}
    except (ValueError, TypeError, AttributeError, EOFError, zipfile.BadZipFile) as error:
        raise ValueError(wrong) from error
    if any(name not in arrays for name in NEEDED) or arrays["x"].shape != arrays["values"].shape:
        raise ValueError(wrong)
    return arrays


@registry.command("response load", "FIL.npz: läs en sparad respons (samma roi, kanal och axis som nu)",
                  "response load FIL.npz")
def cmd_response_load(state, args):
    """Kommandot response load FIL.npz: som response build, men responsen läses ur filen; response on behövs sedan.

    En annan kalibrering ger en varning (responsen läses vid sina våglängder i nm), inte ett fel.
    Fel: ValueError med input.missing_data utan kalibrering, input.invalid_argument om filen inte är en responsfil eller
    gjordes för en annan roi, kanal eller axis; OSError om filen saknas.
    """
    registry.need(args, ("FIL",), "response load")
    if state["coefficients"] is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    saved = _load(args[0])
    cfg = state["settings"]
    roi = tuple(int(v) for v in saved["roi"]) or None
    for name, then, now in (("roi", _roi_text(roi), _roi_text(cfg["roi"])),
                            ("kanal", str(saved["channel"]), cfg["channel"]),
                            ("axis", str(saved["axis"]), cfg["axis"])):
        if then != now:
            raise ValueError(f"input.invalid_argument: responsen gjordes för {name} {then}, nu {name} {now}")
    if not np.array_equal(saved.get("coefficients", np.array([])), state["coefficients"]):
        out.warn("kalibreringen är en annan än när responsen gjordes")
    values = saved["values"]
    state["response"] = {"x": saved["x"], "values": values,
                         "frames": int(saved.get("frames", 0)) or None, "known_file": str(saved.get("known_file", "")) or None}
    taken = str(saved.get("taken", ""))
    session.mark_taken(state, "response", datetime.fromisoformat(taken) if taken else None)
    state["spectrum"] = None
    out.say(f"respons: laddad ur {args[0]}, {np.count_nonzero(np.isfinite(values))} av {len(values)} positioner giltiga")
