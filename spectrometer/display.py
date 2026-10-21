"""Vad fönstret ska visa, räknat ur state: rubrik, varningar, referens, jämförelser, kamerabild, analyspanel, tangenter.

Ritar inget själv: resultatet läggs i fönstrets ordbok (win) och plot.py ritar. Allt här är bara visning;
sparade värden ändras aldrig (normering och frusen kurva finns bara i fönstret). Analyspanelerna colour, rgb, droop,
edge och performance (1.2.16) visar det kommandona senast räknade (remember), aldrig en ny beräkning.
"""

import time

import numpy as np

from spectrometer import calc, plot, session

COUNTS_TOP = {"sum": 800.0}  # fast y-skala för counts: 0-270 (255 plus marginal), summan av tre kanaler 0-800
YSCALES = ("fast", "auto", "zoom")  # tangenten y växlar i den här ordningen
KEYS_HELP = "s spara · p paus · f frys · c rensa · y skala · n normera · h hjälp · q stopp"
PANELS = ("peaks", "calibration", "transmission", "response", "colour", "rgb", "droop", "edge", "performance")
# Panelen och kommandot vars senaste resultat den visar (remember); panelen räknar inget själv (rev7 4E).
RESULTS = {"colour": "color", "rgb": "mix", "droop": "series plot NAMN", "edge": "bandgap", "performance": "perf"}


def window_info(state):
    """Det som står still under en live-körning: fönstertitel, rubrikens första rad, vyn, referens och jämförelser."""
    kind, value = state["settings"]["source"]
    return {
        "name": f"spektro - {kind} {value} - {state['mode']}",
        "view": state["view"],
        "head": session.describe(state),
        "ref": reference_curve(state),
        "compare": [(c["x"], c["values"], c["label"]) for c in state["view"]["compare"]
                    if (c["x_label"], c["y_label"]) == units(state)],  # bara kurvor med samma enheter som live
        "axis": state["settings"]["axis"],
        "laps": [],
    }


def units(state):
    """Axeltexterna som nästa mätning får, (x_label, y_label), efter samma regler som measure."""
    x_label = "pixel" if state["coefficients"] is None else "våglängd (nm)"
    if state["mode"] == "transmission":
        return x_label, "transmission (kvot)"
    if state["use_response"]:
        return x_label, "korrigerad signal (relativ)"
    return x_label, "signal (counts)"


def reference_curve(state):
    """Referensen som (x, värden med NaN) när den går att jämföra med live-kurvan: counts med samma x-enhet."""
    ref = state["reference"]
    if ref is None or units(state) != (ref["x_label"], "signal (counts)"):
        return None
    return ref["x"], np.where(ref["mask"], ref["values"], np.nan)


def frame_info(state, win, spectrum, values):
    """Det som ändras varje varv: rubrik med topp och bilder/s, varningar, 100 %-linje, fotrad, kamerabild och panel.

    values: kurvan som ritas (NaN där masken är falsk). Bilder/s är medlet över de senaste 10 varven.
    """
    laps = win.setdefault("laps", [])
    laps.append(time.perf_counter())
    del laps[:-11]  # 11 tider ger 10 varv
    x = spectrum["x"]
    full = spectrum.get("saturated_px", 0) > 0  # flest mättade ROI-pixlar i någon bild i mätningen (measure.compute)
    warnings = ["MÄTTAD - sänk exponeringen"] if full else []
    transmission = spectrum["y_label"] == "transmission (kvot)"
    if transmission:
        over = int(np.count_nonzero(values[np.isfinite(values)] > 1))
        if over:
            warnings.append(f"T > 1 på {over} {'position' if over == 1 else 'positioner'}")
    text = "ingen giltig position"
    if np.any(np.isfinite(values)):
        i = int(np.nanargmax(values))
        text = f"Topp {values[i]:g} vid {spectrum['x_label']} {x[i]:g}"
    if len(laps) > 1 and laps[-1] > laps[0]:
        text += f" · {(len(laps) - 1) / (laps[-1] - laps[0]):.1f} bilder/s"
    image = state["image"]
    return {
        "title": f"{win.get('head', '')}\n{text}",
        "warn": " · ".join(warnings) or None,
        "guide": ([x[0], x[-1]], [1.0, 1.0]) if transmission else None,
        "foot": f"{session.chain(state)} · frames {state['settings']['frames']} · mättad {'ja' if full else 'nej'}",
        "status": " · ".join(["running", text, *warnings]),
        "image": image,
        "roi": state["settings"]["roi"] or (None if image is None else (0, 0, image.shape[1], image.shape[0])),
        "panel": panel(state, state["view"]["analysis"], spectrum, values) if state["view"]["analysis"] else None,
    }


def fixed_y(state, y_label):
    """Fast y-skala per storhet: counts 0-270 (sum 0-800), transmission 0-1,2, normerad 0-1,1; annars None (auto)."""
    if y_label == "signal (counts)":
        return (0.0, COUNTS_TOP.get(state["settings"]["channel"], 270.0))
    if y_label == "transmission (kvot)":
        return (0.0, 1.2)
    if y_label == "normerad (relativ)":
        return (0.0, 1.1)
    return None


def shown(win, values, y_label):
    """Kurvan som fönstret visar: delad med största giltiga värdet när normalize är på (inte i transmission)."""
    finite = values[np.isfinite(values)]
    if not win.get("view", {}).get("normalize") or y_label == "transmission (kvot)" or finite.size == 0:
        return values, y_label
    if finite.max() <= 0:
        return values, y_label
    return values / finite.max(), "normerad (relativ)"


def draw_spectrum(state, win, spectrum, values):
    """Ritar kurvan som vyn vill ha den (normerad eller inte), med toppmarkör och fast y-skala för storheten."""
    shown_values, y_label = shown(win, values, spectrum["y_label"])
    win["fixed_y"] = fixed_y(state, y_label)
    win["peak"] = None
    if np.any(np.isfinite(shown_values)):
        i = int(np.nanargmax(shown_values))
        win["peak"] = ([spectrum["x"][i]], [shown_values[i]])
    plot.draw(win, spectrum["x"], shown_values, spectrum["x_label"], y_label)


def view_key(win, key, spectrum, values):
    """Tangenterna som bara ändrar visningen: f frys kurvan, c rensa den, y skala, n normera, h hjälptext."""
    if key == "f":
        win["frozen"] = (spectrum["x"].copy(), shown(win, values, spectrum["y_label"])[0].copy())
        win["frozen_label"] = f"frusen {time.strftime('%H:%M:%S')}"
    elif key == "c":
        win["frozen"] = None
    elif key == "y":
        win["yscale"] = YSCALES[(YSCALES.index(win.get("yscale", "fast")) + 1) % len(YSCALES)]
    elif key == "n":
        view = win.setdefault("view", {})
        view["normalize"] = not view.get("normalize", False)
    elif key == "h":
        win["help"] = None if win.get("help") else KEYS_HELP


def save_png(state, folder):
    """Rapportfiguren folder/spectrum.png ur senaste mätningen: ljust tema, mätmappen och inställningarna i rubriken."""
    spectrum = state["spectrum"]
    values = np.where(spectrum["mask"], spectrum["values"], np.nan)
    title = f"{folder.name} · {session.describe(state)} · frames {state['settings']['frames']}"
    plot.save_png(folder / "spectrum.png", spectrum["x"], values, spectrum["x_label"], spectrum["y_label"], title)


def panel(state, name, spectrum, values):
    """Analyspanelen name ur det som redan finns i state; räknar ingen ny analys. Ordboken ritas av plot.

    Nycklar: title, x_label, lines [(x, y, namn)], points (x, y) eller None, text (kort tabell); valfritt y_label,
    marker (punkternas markör), equal (lika skala på axlarna, för xy-diagrammen) och legend (kurvornas namn).
    """
    if name == "peaks":
        x = spectrum["x"]
        y = np.where(np.isfinite(values), values, -np.inf)
        half = max(2, len(y) // 20)  # en topp är störst inom ±5 % av kurvans längd och över 5 % av största värdet
        local = np.lib.stride_tricks.sliding_window_view(np.pad(y, half, constant_values=-np.inf), 2 * half + 1)
        first = y > np.concatenate(([-np.inf], y[:-1]))  # bara första punkten på en platå
        top = np.flatnonzero((y == local.max(axis=1)) & first & np.isfinite(y) & (y >= 0.05 * y.max()))
        top = top[np.argsort(-y[top])][:5]  # de fem högsta, bara för visning (linjebredd och area ger kommandot fwhm)
        rows = "\n".join(f"{x[i]:>8.5g} {values[i]:>8.4g}" for i in top) or "inga toppar"
        return {"title": "peaks: toppar i kurvan", "x_label": spectrum["x_label"], "lines": [(x, values, "kurvan")],
                "points": (x[top], values[top]), "text": f"{'x':>8} {'värde':>8}\n{rows}"}
    if name == "calibration":
        if state["coefficients"] is None:
            return _unavailable(name, "ingen kalibrering. Kör calibrate.")
        low, high = state["pixel_range"]
        pixels = np.linspace(low, high, 50)
        terms = ", ".join(f"a{i} {c:g}" for i, c in enumerate(state["coefficients"]))
        return {"title": "calibration: pixel till nm", "x_label": "pixel", "points": None,
                "lines": [(pixels, calc.evaluate_wavelength(pixels, state["coefficients"]), "nm")],
                "text": f"{terms}\ngiltigt: pixel {low:g} till {high:g}"}
    if name == "transmission":
        ref = state["reference"]
        if ref is None:
            return _unavailable(name, "ingen referens. Kör reference.")
        lines = [(ref["x"], np.where(ref["mask"], ref["values"], np.nan), "referens")]
        if spectrum["y_label"] == "signal (counts)" and np.array_equal(spectrum["x"], ref["x"]):
            lines.append((spectrum["x"], values, "prov"))
        return {"title": "transmission: referensen (counts)", "x_label": ref["x_label"], "lines": lines, "points": None,
                "text": f"{np.count_nonzero(ref['mask'])} giltiga positioner\nkanal {ref['channel']} · mode {state['mode']}"}
    if name == "response":
        response = state["response"]
        if response is None:
            return _unavailable(name, "ingen respons. Kör response build.")
        valid = np.count_nonzero(np.isfinite(response["values"]))
        return {"title": "response: relativ respons", "x_label": "våglängd (nm)", "points": None,
                "lines": [(response["x"], response["values"], "respons")],
                "text": f"{valid} av {len(response['values'])} giltiga\nrespons {'på' if state['use_response'] else 'av'}"}
    found = state["view"].get("results", {}).get(name)  # övriga paneler är nycklarna i RESULTS (view_cmds kollar namnet)
    if found is None:
        return _unavailable(name, f"inget resultat än. Kör {RESULTS[name]}.")
    return PANEL_BUILDERS[name](found)


def remember(state, name, result):
    """Sparar ett analysresultat för panelen name (en nyckel i RESULTS) i state["view"]. 1.2.16.

    Kommandot (color, mix, series plot, bandgap, perf) räknar och lämnar resultatet här; panelen visar det senaste
    utan att räkna om. Bara visning: undo och mätningarna rör det inte, reset tar bort det.
    """
    state["view"].setdefault("results", {})[name] = result


def _closed(x, y):
    """Kurvan med första punkten sist också: hästskon sluten med purpurlinjen."""
    return np.append(x, x[0]), np.append(y, y[0])


def _colour(found):
    """colour: punkten i CIE 1931 xy med hästskon och Planck-kurvan; CCT och Duv i tabellen."""
    x, y = found["xy"]
    cct = "ingen CCT (|Duv| över 0,01)" if found["cct"] is None else f"CCT {found['cct']:.0f} K"
    return {"title": "colour: CIE 1931 xy", "x_label": "x", "y_label": "y", "equal": True, "marker": "o",
            "lines": [(*_closed(*found["locus"]), "spektralkurvan"), (*found["planck"], "Planck")],
            "points": ([x], [y]), "text": f"x {x:.4f}  y {y:.4f}\n{cct}\nDuv {found['duv']:+.4f}"}


def _rgb(found):
    """rgb: de tre LED:erna, triangeln de spänner och blandningen (eller målfärgerna i --sweep), vikterna i tabellen."""
    corners = found["corners"]
    tx, ty = _closed([c[0] for c in corners], [c[1] for c in corners])
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    if found.get("blend") is not None:
        xs, ys = xs + [found["blend"][0]], ys + [found["blend"][1]]
    rows = [f"{name}: x {x:.3f} y {y:.3f}" for name, (x, y) in zip("RGB", corners)]
    if found.get("weights") is not None:
        w = found["weights"]
        rows.append(f"vikter R {w[0]:.3f} G {w[1]:.3f} B {w[2]:.3f}")
    for name, x, y, enough in found.get("targets", []):
        xs, ys = xs + [x], ys + [y]
        rows.append(f"{name}: {'räcker' if enough else 'räcker inte'}")
    return {"title": "rgb: blandning av tre LED", "x_label": "x", "y_label": "y", "equal": True, "marker": "o",
            "lines": [(*_closed(*found["locus"]), "spektralkurvan"), (tx, ty, "triangeln")], "points": (xs, ys),
            "text": "\n".join(rows)}


def _droop(found):
    """droop: relativ uteffekt (delad med sitt max) och area/I (droop) mot strömmen, per serie."""
    lines, rows = [], []
    for name, xs, areas, eff in found["curves"]:
        top = np.nanmax(areas) if np.any(np.isfinite(areas)) else 1.0
        lines.append((xs, areas / top, f"{name} uteffekt"))
        if eff is not None:
            lines.append((xs, eff, f"{name} area/I"))
            if xs.size >= 2:
                rows.append(f"{name}: droop {100 * (1 - eff[-1]):.0f} %")
        rows.append(f"{name}: {xs.size} punkter")
    return {"title": "droop: relativt, inte verkningsgrad", "x_label": found["x_label"], "y_label": "relativ",
            "lines": lines, "points": None, "text": "\n".join(rows), "legend": True}


def _edge(found):
    """edge: absorbansen mot fotonenergin och den anpassade kanten; E_g i tabellen."""
    E, A = found["E"], found["A"]
    return {"title": f"edge: {found['method']}", "x_label": "fotonenergi (eV)", "y_label": "absorbans",
            "lines": [(E, A, "absorbans"), (*found["line"], "kanten")], "points": ([found["point"][0]], [found["point"][1]]),
            "marker": "o", "legend": True, "text": f"E_g {found['eg']:.3f} eV\n{found['nm']:.1f} nm"}


def _performance(found):
    """performance: tiden för läs och räkna per mätning ur perf, median och bilder/s i tabellen."""
    reads, computes = found["read_ms"], found["compute_ms"]
    k = np.arange(1, reads.size + 1)
    return {"title": "performance: perf", "x_label": "mätning", "y_label": "ms", "points": None,
            "lines": [(k, reads, "läs"), (k, computes, "räkna")], "legend": True,
            "text": f"läs median {np.median(reads):.2f} ms\nräkna median {np.median(computes):.2f} ms\n"
                    f"{found['rate']:.1f} bilder/s"}


PANEL_BUILDERS = {"colour": _colour, "rgb": _rgb, "droop": _droop, "edge": _edge, "performance": _performance}


def _unavailable(name, why):
    """En panel utan data: bara texten otillgängligt och varför, aldrig påhittade värden."""
    return {"title": name, "x_label": "", "lines": [], "points": None, "text": f"otillgängligt: {why}"}
