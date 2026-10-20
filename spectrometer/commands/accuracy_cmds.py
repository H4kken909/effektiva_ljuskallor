"""repeat, linearity och calibrate save: repeterbarhet, linjäritet och kalibreringens osäkerhet till rapporten (M12)."""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from spectrometer import calc, files, measure, out, registry
from spectrometer.analysis import peaks


def _peak_and_area(spectrum):
    """(toppvärde, toppläge, area) för en mätning: högsta giltiga värdet, dess x och trapetsarean över de giltiga."""
    x, values, mask = spectrum["x"], spectrum["values"], spectrum["mask"]
    if not mask.any():
        raise ValueError("input.missing_data: ingen giltig position i spektrumet")
    i = int(np.nanargmax(np.where(mask, values, np.nan)))
    return values[i], x[i], float(np.trapezoid(values[mask], x[mask]))


def _spread(name, values, unit="", percent=True):
    """En rad med medel och spridning (stickprov, ddof=1), med spridningen i % av medlet om percent."""
    mean, sd = float(np.mean(values)), float(np.std(values, ddof=1))
    share = f" ({100 * sd / abs(mean):.2f} %)" if percent and mean != 0 else ""
    return f"{name}: medel {out.fmt(mean)}{unit}, spridning {out.fmt(sd)}{unit}{share}"


@registry.command("repeat", "N [UT.csv]: mät N gånger; medel och spridning för topp, toppläge och area, per position i UT.csv",
                  "repeat N [UT.csv]")
def cmd_repeat(state, args):
    """Kommandot repeat N [UT.csv]: N mätningar i rad med samma källa och inställningar; senaste mätningen står kvar.

    Skriver medel och spridning (stickprov, ddof=1, RX06) för toppvärdet, toppläget och arean, och sparar medel och
    spridning per position i UT.csv (utan UT.csv: repeat-ÅÅÅÅMMDD-HHMMSS.csv i output_dir). Spridningen visar
    repeterbarheten, inte noggrannheten: ett fel som är lika i varje mätning syns inte.

    Fel: ValueError med input.invalid_argument vid fel ord eller om UT.csv redan finns; felen ur measure.
    """
    if not 1 <= len(args) <= 2:
        raise ValueError("input.invalid_argument: repeat tar N och eventuellt UT.csv")
    n = registry.to_int("N", args[0], 2)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(args[1]) if len(args) == 2 else Path(state["settings"]["output_dir"]) / f"repeat-{stamp}.csv"
    if path.exists():
        raise ValueError(f"input.invalid_argument: {path.as_posix()} finns redan, välj ett annat namn")
    copy = state.copy()  # measure lägger mätningarna i kopian
    spectra = measure._with_source(state, None, lambda src: [measure.measure(copy, src) for _ in range(n)])
    numbers = np.array([_peak_and_area(spectrum) for spectrum in spectra])
    calibrated = state["coefficients"] is not None
    frames = state["settings"]["frames"]
    out.say(f"repeat: {n} mätningar med {frames} {'bild' if frames == 1 else 'bilder'} var")
    out.say(_spread("topp", numbers[:, 0]))
    out.say(_spread("toppläge", numbers[:, 1], " nm" if calibrated else " pixel", percent=False))
    out.say(_spread("area", numbers[:, 2]))
    mean, stddev = calc.average_spectra(np.stack([spectrum["values"] for spectrum in spectra]))
    valid = np.logical_and.reduce([spectrum["mask"] for spectrum in spectra])
    path.parent.mkdir(parents=True, exist_ok=True)
    files.save_columns(path, [("x_nm" if calibrated else "x_px", spectra[0]["x"]), ("mean", mean), ("stddev", stddev),
                              ("valid", ["true" if ok else "false" for ok in valid])])
    out.say(f"Sparad i {path.as_posix()}")


def _asked(state, prompt):
    """Kamera i en terminal: väntar på Enter efter prompten; False om svaret är avbryt. Fil eller pipad: True."""
    if state["settings"]["source"][0] != "camera" or not sys.stdin.isatty():
        return True
    try:
        return out.ask(prompt).strip().lower() != "avbryt"
    except EOFError:
        return False


@registry.command("linearity", "E1 E2 E3 ...: arean vid varje exponering och avvikelsen från en rät linje",
                  "linearity E1 E2 E3 [E4 ...]")
def cmd_linearity(state, args):
    """Kommandot linearity E1 E2 E3 [E4 ...]: en mätning per exponering, arean och avvikelsen från en rät linje.

    Exponeringen ställer du själv (v4l2-ctl eller drivrutinens ruta); med kamera i en terminal frågar programmet före
    varje mätning. Droop och serier kräver en linjär detektor: arean ska växa som exponeringen. Talen är relativa.

    Fel: ValueError med input.invalid_argument vid färre än tre olika exponeringar, ett ord som inte är ett tal,
    eller avbryt; felen ur measure.
    """
    exposures = np.array([registry.to_float("E", word, 0) for word in args])
    if len(set(exposures)) < 3 or len(set(exposures)) < len(exposures):
        raise ValueError("input.invalid_argument: linearity behöver minst tre olika exponeringar (E1 E2 E3)")
    copy = state.copy()

    def series(src):
        found = []
        for exposure in exposures:
            if not _asked(state, f"Ställ exponeringen på {exposure:g} och tryck Enter (avbryt stoppar): "):
                raise ValueError("input.invalid_argument: linearity avbruten")
            found.append(measure.measure(copy, src))
        return found

    spectra = measure._with_source(state, None, series)
    areas = np.array([_peak_and_area(spectrum)[2] for spectrum in spectra])
    slope, intercept = np.polyfit(exposures, areas, 1)
    line = slope * exposures + intercept
    intercept = round(intercept, 6) + 0.0  # -0.0 och 1e-15 blir 0
    out.say(f"rät linje: area = {slope:.4g}·E {'+' if intercept >= 0 else '-'} {abs(intercept):.4g}")
    for exposure, area, fitted, spectrum in zip(exposures, areas, line, spectra):
        out.say(f"exponering {exposure:g}: area {area:.4g}, avvikelse {100 * (area - fitted) / fitted:+.1f} %")
        if spectrum["saturated_px"]:
            out.warn(f"mättad vid exponering {exposure:g}: den punkten säger inget om linjäriteten")
    worst = float(np.max(np.abs(areas - line) / np.abs(line)))
    out.say(f"största avvikelse från en rät linje: {100 * worst:.1f} %")


def _resolution(state):
    """FWHM i nm för högsta toppen i senaste mätningen (en smal linje ger upplösningen), eller None om den saknas."""
    spectrum = state["spectrum"]
    if spectrum is None or not spectrum["mask"].any():
        return None
    values = np.where(spectrum["mask"], spectrum["values"], np.nan)
    width = peaks.fwhm(spectrum["x"], values, int(np.nanargmax(values)))
    return float(width) if np.isfinite(width) else None


@registry.command("calibrate save", "FIL.json: spara kalibreringen med residualer, kontrollfel och upplösning (resolution_nm)",
                  "calibrate save FIL.json")
def cmd_calibrate_save(state, args):
    """Kommandot calibrate save FIL.json: kalibreringen med residualer, kontrollfel, rms, nm per pixel och upplösning.

    Punktfilen läses igen (samma sha256 som vid calibrate). Upplösningen är FWHM för högsta toppen i senaste
    mätningen: mät lysröret eller lasern med step efter calibrate. Skriver aldrig över en fil.

    Fel: ValueError med input.missing_data utan kalibrering eller punktfil, med input.invalid_argument om punktfilen
    har ändrats eller FIL.json redan finns; OSError om filen inte går att skriva.
    """
    registry.need(args, ("FIL.json",), "calibrate save")
    coefficients = state["coefficients"]
    if coefficients is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    points_file = state["calibration_points_file"]
    if points_file is None or not Path(points_file["path"]).is_file():
        raise ValueError("input.missing_data: punktfilen finns inte, kör calibrate PUNKTFIL.csv först")
    if files.points_file_info(points_file["path"])["sha256"] != points_file["sha256"]:
        raise ValueError("input.invalid_argument: punktfilen har ändrats sedan calibrate, kör calibrate igen")
    if Path(args[0]).exists():
        raise ValueError(f"input.invalid_argument: {args[0]} finns redan, välj ett annat namn")
    pixels, wavelengths, is_check = files.load_points(points_file["path"])
    # Residual för en anpassningspunkt, kontrollfel för check 1; avrundat till 1e-6 nm som i calibrate.
    errors = np.round(wavelengths - calc.evaluate_wavelength(pixels, coefficients), 6) + 0.0
    fit, check = errors[~is_check], errors[is_check]
    rms = float(np.sqrt(np.mean(fit**2)))
    middle = float(np.mean(state["pixel_range"]))
    nm_per_pixel = float(np.abs(np.diff(calc.evaluate_wavelength(np.array([middle, middle + 1]), coefficients)))[0])
    resolution = _resolution(state)
    files.save_json(args[0], {
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "points_file": points_file,
        "coefficients": coefficients.tolist(),
        "pixel_range": [float(v) for v in state["pixel_range"]],
        "points": [{"pixel": float(p), "wavelength_nm": float(w), "check": bool(c), "error_nm": float(e)}
                   for p, w, c, e in zip(pixels, wavelengths, is_check, errors)],
        "rms_nm": rms,
        "max_check_error_nm": float(np.max(np.abs(check))) if check.size else None,
        "nm_per_pixel": nm_per_pixel,
        "resolution_nm": resolution,
    })
    out.say(f"kalibrering: rms {out.fmt(rms)} nm över {fit.size} anpassningspunkter, {out.fmt(nm_per_pixel)} nm per pixel")
    if fit.size <= coefficients.size:
        out.warn("lika många punkter som koefficienter: residualerna är 0 per definition, lägg till punkter")
    if check.size:
        word = "kontrollpunkt" if check.size == 1 else "kontrollpunkter"
        out.say(f"kontrollfel: största {out.fmt(np.max(np.abs(check)))} nm ({check.size} {word})")
    else:
        out.say("kontrollfel: inga kontrollpunkter i filen")
    if resolution is None:
        out.say("upplösning: okänd (mät en smal linje med step efter calibrate)")
    else:
        out.say(f"upplösning: {out.fmt(resolution)} nm (FWHM för högsta toppen i senaste mätningen)")
    out.say(f"Sparad i {args[0]}")
