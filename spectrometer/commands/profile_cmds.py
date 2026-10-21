"""response save och load: responsen som .npz med roi, kanal, axis och kalibrering; dark save och load: .npy."""

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


@registry.command("response save",
                  "FIL.npz: spara responsen med roi, kanal, axis och kalibrering (skriver aldrig över)",
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
        "frames": np.array(response["frames"] or 0),
        "known_file": np.array(response["known_file"] or ""),
        "taken": np.array(taken.isoformat(timespec="seconds") if taken else ""),
    }
    with registry.open_new(args[0], "xb", "response save") as f:
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
    state["response"] = {"x": saved["x"], "values": values, "frames": int(saved.get("frames", 0)) or None,
                         "known_file": str(saved.get("known_file", "")) or None}
    taken = str(saved.get("taken", ""))
    session.mark_taken(state, "response", datetime.fromisoformat(taken) if taken else None)
    state["spectrum"] = None
    out.say(f"respons: laddad ur {args[0]}, "
            f"{np.count_nonzero(np.isfinite(values))} av {len(values)} positioner giltiga")


@registry.command("dark save", "FIL.npy: spara mörkret (hela bilden) som .npy (skriver aldrig över)",
                  "dark save FIL.npy")
def cmd_dark_save(state, args):
    """Kommandot dark save FIL.npy: mörkret, (H, W, 3) i counts, med np.save som float32 (halva filen). 1.2.14.

    Fel: ValueError med input.missing_data utan mörker, input.invalid_argument om FIL redan finns; OSError om den inte
    går att skriva.
    """
    registry.need(args, ("FIL",), "dark save")
    if state["dark"] is None:
        raise ValueError("input.missing_data: inget mörker, kör dark först")
    with registry.open_new(args[0], "xb", "dark save") as f:
        np.save(f, state["dark"].astype(np.float32))
    height, width = state["dark"].shape[:2]
    out.say(f"mörker: sparat i {args[0]} ({width} x {height} pixlar)")


def _load_dark(path):
    """Mörkret i en .npy från dark save som float64, läst utan pickle (allow_pickle=False: filen kan inte köra kod).

    Fel: ValueError med input.invalid_argument om filen saknas eller inte är ett mörker (H, W, 3) med ändliga tal;
    OSError om den inte går att läsa.
    """
    if not Path(path).is_file():
        raise ValueError(f"input.invalid_argument: {Path(path).as_posix()} finns inte")
    wrong = f"input.invalid_argument: {Path(path).name} är inget mörker från dark save"
    try:
        dark = np.load(path, allow_pickle=False)
    except (ValueError, EOFError) as error:
        raise ValueError(wrong) from error
    if not isinstance(dark, np.ndarray):  # en .npz ger flera arrayer, inte ett mörker
        dark.close()
        raise ValueError(wrong)
    if dark.ndim != 3 or dark.shape[2] != 3 or dark.dtype.kind not in "fiu" or not np.all(np.isfinite(dark)):
        raise ValueError(wrong)
    return dark.astype(np.float64)


@registry.command("dark load", "FIL.npy: läs ett sparat mörker (samma bildstorlek, samma exponering och gain som då)",
                  "dark load FIL.npy")
def cmd_dark_load(state, args):
    """Kommandot dark load FIL.npy: som dark, men mörkret läses ur filen. 1.2.14.

    Formen prövas mot senaste bilden ur källan och mot ROI:n; finns ingen bild än prövas den vid nästa mätning.
    Exponering och gain står inte i filen, så programmet varnar alltid. Tiden för mörkret är filens ändringstid.
    Referensen tas bort, som efter dark. Fel: ValueError med input.invalid_argument om filen saknas, inte är ett
    mörker eller inte passar bilden eller ROI:n.
    """
    registry.need(args, ("FIL",), "dark load")
    dark = _load_dark(args[0])
    height, width = dark.shape[:2]
    image = state["image"]
    if image is not None and image.shape != dark.shape:
        raise ValueError(f"input.invalid_argument: mörkret är {width} x {height} pixlar men bilden ur källan är "
                         f"{image.shape[1]} x {image.shape[0]}")
    roi = state["settings"]["roi"]
    if roi is not None and (roi[0] + roi[2] > width or roi[1] + roi[3] > height):
        raise ValueError(f"input.invalid_argument: roi {_roi_text(roi)} ligger utanför mörkret "
                         f"({width} x {height} pixlar)")
    state["dark"], state["dark_frames"], state["dark_camera"] = dark, None, None
    session.mark_taken(state, "dark", datetime.fromtimestamp(Path(args[0]).stat().st_mtime).astimezone())
    state["spectrum"] = None
    out.say(f"mörker: laddat ur {args[0]}, {width} x {height} pixlar, medel {out.fmt(np.mean(dark))}")
    if image is None:
        out.say("Bildstorleken prövas mot källan vid nästa mätning.")
    out.warn("mörkret gäller bara med samma exponering och gain som när det mättes (filen säger inte vilka)")
    session.after_new_dark(state)
