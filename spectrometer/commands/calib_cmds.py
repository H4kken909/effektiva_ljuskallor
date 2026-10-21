"""calibrate och toppar: våglängd ur en punktfil, och topparna som punktfilen byggs av."""

import numpy as np

from spectrometer import calc, files, measure, out, peaks, registry, session


@registry.command("calibrate", "PATH [DEGREE [MARGIN]]: anpassa våglängd till en punktfil", "calibrate PATH [DEGREE [MARGIN]]")
def cmd_calibrate(state, args):
    """Kommandot calibrate PATH [DEGREE [MARGIN]]: anpassar våglängden till punktfilen och prövar mot kontrollpunkterna.

    Fel: ValueError med input.invalid_argument vid fel ord, fel i punktfilen, för få punkter eller en linje som inte
    är monoton i det giltiga intervallet; OSError om filen saknas. Den gamla kalibreringen står då kvar.
    """
    if not args:
        registry.need(args, ("PATH",), "calibrate")
    if args[0].lower().endswith(".json"):
        load_settings_calibration(state, args)
        return
    if len(args) > 3:
        raise ValueError("input.invalid_argument: calibrate tar högst tre ord (PATH DEGREE MARGIN)")
    degree = registry.to_int("DEGREE", args[1], 1) if len(args) >= 2 else 1
    margin = to_margin(args[2]) if len(args) == 3 else 1.0
    pixels, wavelengths, is_check = files.load_points(args[0])
    fit_pixels, fit_wavelengths = pixels[~is_check], wavelengths[~is_check]
    check_pixels, check_wavelengths = pixels[is_check], wavelengths[is_check]
    coefficients = calc.fit_wavelength(fit_pixels, fit_wavelengths, degree)  # bara anpassningspunkter
    _say_coefficients(coefficients)
    valid_range = _valid_range(fit_pixels, coefficients, margin)
    residuals = fit_wavelengths - calc.evaluate_wavelength(fit_pixels, coefficients)
    for pixel, residual, step in zip(fit_pixels, residuals, _nm_per_pixel(fit_pixels, coefficients)):
        out.say(f"residual: {out.fmt(round(residual, 6) + 0.0)}")
        if abs(residual) > step:
            out.warn(f"residualen {out.fmt(residual)} nm vid pixel {out.fmt(pixel)} är större än steget "
                     f"{out.fmt(step)} nm. Hör pixeln till rätt linje?")
    check_errors = check_wavelengths - calc.evaluate_wavelength(check_pixels, coefficients)
    for pixel, error, step in zip(check_pixels, check_errors, _nm_per_pixel(check_pixels, coefficients)):
        out.say(f"kontrollfel vid pixel {out.fmt(pixel)}: {out.fmt(error)}")
        if abs(error) > step:
            out.warn(f"kontrollfelet {out.fmt(error)} nm är större än steget {out.fmt(step)} nm.")
    if check_pixels.size == 0:
        out.say("inte kontrollerad: inga kontrollpunkter i filen")
    fit_range = (np.min(fit_pixels), np.max(fit_pixels))
    _set_calibration(state, coefficients, valid_range, fit_range, files.points_file_info(args[0]))


def _valid_range(fit_pixels, coefficients, margin):
    """Det giltiga intervallet (låg, hög) i pixlar: de anpassade pixlarna och margin gånger deras bredd på var sida.

    Linjen måste vara monoton i intervallet, annars får två pixlar samma våglängd.
    Fel: ValueError med input.invalid_argument om den inte är det.
    """
    low, high = np.min(fit_pixels), np.max(fit_pixels)
    width = high - low
    valid_range = (max(low - margin * width, 0), high + margin * width)
    out.say(f"anpassat: pixel {out.fmt(low)} till {out.fmt(high)}")
    out.say(f"giltigt: pixel {out.fmt(valid_range[0])} till {out.fmt(valid_range[1])}")
    test_pixels = np.arange(valid_range[0], valid_range[1] + 1, dtype=np.float64)
    diffs = np.diff(calc.evaluate_wavelength(test_pixels, coefficients))
    turn = turning_point(coefficients)
    if not (np.all(diffs > 0) or np.all(diffs < 0)):
        hint = f"; grad 2 vänder vid pixel {turn:.0f}; prova grad 1 eller fler punkter" if turn is not None else ""
        raise ValueError(
            f"input.invalid_argument: inte monoton mellan pixel {out.fmt(valid_range[0])} och "
            f"{out.fmt(valid_range[1])}{hint}"
        )
    if turn is not None:
        out.say(f"grad 2 vänder vid pixel {turn:.0f}, utanför giltigt intervall")
    return valid_range


def _say_coefficients(coefficients):
    """a0, a1 och för grad 2 a2, en rad var."""
    out.say(f"a0: {out.fmt(coefficients[0])} nm")
    out.say(f"a1: {out.fmt(coefficients[1])} nm/pixel")
    if coefficients.size == 3:
        out.say(f"a2: {out.fmt(coefficients[2])} nm/pixel^2")


def _nm_per_pixel(pixels, coefficients):
    """Lokalt steg: hur många nm en pixel är vid pixels; ett fel större än steget är värt en varning."""
    return np.abs(calc.evaluate_wavelength(pixels + 1, coefficients) - calc.evaluate_wavelength(pixels, coefficients))


def _set_calibration(state, coefficients, pixel_range, fit_range, points_file):
    """Lägger kalibreringen i state, glömmer responsen om x i nm ändrats och glömmer mätningen."""
    _forget_response_if_changed(state, coefficients)
    state["coefficients"] = coefficients
    state["pixel_range"] = pixel_range
    state["fit_range"] = fit_range
    state["calibration_points_file"] = points_file
    session.mark_taken(state, "calibrate")
    state["spectrum"] = None


PEAK_MIN_FRACTION = 0.1  # en topp ska vara minst 10 % av det högsta giltiga värdet (antaget, prova vid riggen)
PEAK_MIN_DISTANCE = 3  # toppar närmare än 3 pixlar slås ihop till den högsta


def spectrum_peaks(state, n):
    """De n högsta topparna i senaste mätningen som (pixel, värde), i stigande pixel.

    Pixeln räknas i hela bilden (inte plats i ROI:n), med delpixel från peaks.refine_peak avrundad till 0.1 pixel.
    Fel: ValueError med input.missing_data om ingen mätning finns.
    """
    spectrum = registry.need_spectrum(state)
    if "loaded_from" in spectrum:  # 1.2.2
        raise ValueError("input.invalid_argument: toppar fungerar efter step, inte efter load (pixlarna räknas ur nuvarande roi)")
    image = state["image"]
    roi = calc.roi_or_whole(state["settings"]["roi"], image)
    pixels = measure.pixel_axis(roi, state["settings"]["axis"])
    # Samma vändning som spektrumet fick i measure, så att pixels[k] hör till values[k].
    _x, pixels, _mask, _label = measure.calibrate_axis(state, pixels, pixels, np.ones(pixels.size, dtype=bool))
    if not spectrum["mask"].any():
        return []
    values = calc.masked_values(spectrum)
    min_height = PEAK_MIN_FRACTION * np.max(spectrum["values"][spectrum["mask"]])
    found = []
    for i in peaks.find_peaks(spectrum["values"], spectrum["mask"], min_height, PEAK_MIN_DISTANCE)[:n]:
        position = peaks.refine_peak(values, i)
        pixel = float(np.interp(position, np.arange(pixels.size), pixels))
        found.append((round(pixel, 1), float(spectrum["values"][i])))
    return sorted(found)


@registry.command("toppar", "[N] eller LINJEFIL [UT.csv]: toppar ur senaste step, med LINJEFIL ett förslag till punktfil")
def cmd_toppar(state, args):
    """Kommandot toppar [N]: de N högsta topparna (efter calibrate även nm); toppar LINJEFIL [UT.csv]: punktfilsförslag.

    Fel: ValueError med input.missing_data utan mätning, input.invalid_argument vid fel ord.
    """
    if len(args) > 2:
        raise ValueError("input.invalid_argument: toppar tar högst två ord (LINJEFIL UT.csv)")
    if args and not args[0].lstrip("-").isdigit():
        propose_points(state, args[0], args[1] if len(args) == 2 else None)
        return
    if len(args) > 1:
        raise ValueError("input.invalid_argument: toppar N tar inga fler ord")
    n = registry.to_int("N", args[0], 1) if args else 5
    found = spectrum_peaks(state, n)
    if not found:
        out.say(f"inga toppar över {PEAK_MIN_FRACTION * 100:g} % av det högsta värdet")
    for k, (pixel, value) in enumerate(found, start=1):
        text = f"topp {k}: pixel {pixel:.1f} värde {out.fmt(value)}"
        if state["coefficients"] is not None:
            nm = calc.evaluate_wavelength(np.array([pixel]), state["coefficients"])[0]
            text += f"  {nm:.1f} nm"
            if state["fit_range"] is not None and not state["fit_range"][0] <= pixel <= state["fit_range"][1]:
                text += "  (utanför anpassat intervall)"
        out.say(text)


MATCH_MARGIN_NM = 1.0  # näst bästa parningen inom 1 nm rms från den bästa: varna (antaget)


def propose_points(state, line_path, out_path):
    """toppar LINJEFIL [UT.csv]: parar topparna med linjerna och skriver förslaget som färdiga rader i en punktfil.

    Programmet kalibrerar inte själv: en människa granskar raderna och kör sedan calibrate. Med out_path skrivs
    filen också (aldrig över en befintlig). Den andra toppen blir kontrollpunkt (check 1) när det finns minst tre.
    Fel: ValueError med input.missing_data utan mätning eller med färre än två toppar; fel ur load_lines och save_points.
    """
    lines = files.load_lines(line_path)
    found = spectrum_peaks(state, lines.size)
    if len(found) < 2:
        raise ValueError(f"input.missing_data: parningen behöver minst två toppar, mätningen har {len(found)}")
    pixels = np.array([pixel for pixel, _value in found])
    chosen, rms, next_rms = peaks.match_peaks(pixels, lines)
    checks = [1 if k == 1 and pixels.size >= 3 else 0 for k in range(pixels.size)]
    rows = [f"{pixel:.1f},{nm:.10g},{check}" for pixel, nm, check in zip(pixels, chosen, checks)]
    out.say(f"förslag: {pixels.size} toppar mot {lines.size} linjer, rms {rms:.2f} nm (granska innan calibrate)")
    out.say("pixel,wavelength_nm,check")
    for row in rows:
        out.say(row)
    if pixels.size < lines.size:
        out.warn(f"{pixels.size} toppar men {lines.size} linjer. Smälter gula dubbletten ihop? Kontrollera parningen.")
    if next_rms - rms < MATCH_MARGIN_NM:
        out.warn(f"näst bästa parningen har rms {next_rms:.2f} nm, nära den bästa. Kontrollera parningen.")
    if out_path is not None:
        files.save_points(out_path, rows)
        out.say(f"punktfil sparad: {out_path}")


def to_margin(text):
    """MARGIN i calibrate: hur stor del av den anpassade bredden som får extrapoleras på var sida (minst 0).

    Fel: ValueError med input.invalid_argument om ordet inte är ett tal eller är mindre än 0.
    """
    try:
        margin = float(text)
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: MARGIN ska vara ett tal, fick {text}") from error
    if not np.isfinite(margin) or margin < 0:
        raise ValueError(f"input.invalid_argument: MARGIN ska vara ett tal minst 0, fick {text}")
    return margin


def turning_point(coefficients):
    """Pixeln där grad 2 vänder (derivatan a1 + 2·a2·p är 0), eller None vid grad 1 eller a2 = 0."""
    if coefficients.size < 3 or coefficients[2] == 0:
        return None
    return -coefficients[1] / (2 * coefficients[2])


def _forget_response_if_changed(state, coefficients):
    """Glömmer responsen när koefficienterna ändras: den gjordes mot x i nm från den gamla kalibreringen. LOG-21."""
    if not np.array_equal(state["coefficients"], coefficients):
        session.forget_response(state)


def load_settings_calibration(state, args):
    """calibrate MAPP/settings.json: koefficienterna och pixel_range ur en sparad mätning, utan residual.

    Varnar när axis eller bildens storlek skiljer sig från nu: då betyder pixlarna olika saker. En annan ROI spelar
    ingen roll, pixlarna räknas i hela bilden. Bildens storlek jämförs bara om en bild redan finns (efter step).
    Fel: ValueError med input.invalid_argument vid fler ord; fel ur files.load_saved_calibration.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: calibrate MAPP/settings.json tar inga fler ord")
    saved = files.load_saved_calibration(args[0])
    coefficients = saved["coefficients"]
    low, high = saved["pixel_range"]
    out.say(f"kalibrering läst ur {args[0]}")
    _say_coefficients(coefficients)
    out.say(f"giltigt: pixel {out.fmt(low)} till {out.fmt(high)}")
    out.say("ingen residual: punkterna finns inte i settings.json")
    axis = state["settings"]["axis"]
    if saved["axis"] is not None and saved["axis"] != axis:
        out.warn(f"axis är {saved['axis']} i settings.json men {axis} nu. Pixlarna betyder olika saker.")
    if state["image"] is not None and saved["image_size"] is not None:
        now = [state["image"].shape[1], state["image"].shape[0]]
        if list(saved["image_size"]) != now:
            width, height = saved["image_size"]
            out.warn(f"bilden var {width}x{height} pixlar men är {now[0]}x{now[1]} nu. Pixlarna betyder olika saker.")
    _set_calibration(state, coefficients, (low, high), None, saved["calibration_points_file"])  # fit_range okänt
