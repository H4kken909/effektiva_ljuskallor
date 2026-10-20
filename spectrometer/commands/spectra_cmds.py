"""load, och från 1.2.3 analysen: läsa tillbaka en mätmapp och räkna på senaste mätningen eller på mappar. 1.2.2.

Inget här mäter. Kamerans tal är relativa: inte watt, lumen eller verkningsgrad.
"""

from pathlib import Path

import numpy as np

from spectrometer import __version__, files, out, plot, registry
from spectrometer.analysis import bandgap, peaks


@registry.command("load", "MAPP: läs en sparad mätmapp till senaste mätningen (graf och view compare add visar den)", "load MAPP")
def cmd_load(state, args):
    """Kommandot load MAPP: spectrum.csv och settings.json ur mätmappen blir senaste mätningen; skriver toppen som step.

    Mappen är redan sparad: save vägrar, och toppar också (den räknar pixlar ur nuvarande roi). Senaste bilden glöms.
    """
    registry.need(args, ("MAPP",), "load")
    spectrum = files.load_measurement(args[0])
    spectrum["loaded_from"] = spectrum["saved_in"] = spectrum["folder"]  # saved_in: quit frågar inte
    state["spectrum"], state["image"] = spectrum, None
    raw = "med raw_counts" if "raw" in spectrum else "utan raw_counts (sparad före 1.2.2)"
    out.say(f"laddad: {spectrum['folder']} ({spectrum['x'].size} positioner, {raw})")
    values = np.where(spectrum["mask"], spectrum["values"], np.nan)
    if not np.any(np.isfinite(values)):
        out.say("ingen giltig position")
        return
    i = int(np.nanargmax(values))
    out.say(f"Topp {out.fmt(values[i])} vid {spectrum['x_label']} {out.fmt(spectrum['x'][i])}")


UNITS = {"signal (counts)": "counts", "korrigerad signal (relativ)": "relativ", "transmission (kvot)": "kvot"}


def latest(state):
    """Senaste mätningen (step eller load) och värdena med NaN där masken är falsk. Fel: input.missing_data utan mätning."""
    spectrum = state["spectrum"]
    if spectrum is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step eller load först.")
    return spectrum, np.where(spectrum["mask"], spectrum["values"], np.nan)


def units(spectrum):
    """(x-enheten, areans enhet): ("nm", "counts·nm") efter calibrate, annars pixel."""
    x_unit = "nm" if spectrum["x_label"] == "våglängd (nm)" else "pixel"
    return x_unit, f"{UNITS.get(spectrum['y_label'], 'relativ')}·{x_unit}"


def summary(spectrum, values, i):
    """Toppen i som (läge, höjd, FWHM): läget är tyngdpunkten över tre punkter, FWHM NaN om kurvan inte når halva höjden."""
    x = spectrum["x"]
    return peaks.centroid(x, values, i), float(values[i]), peaks.fwhm(x, values, i)


@registry.command("fwhm", "[N]: läge, höjd och linjebredd (FWHM) för de N högsta topparna (5), och arean", "fwhm [N]")
def cmd_fwhm(state, args):
    """Kommandot fwhm [N]: topparna i senaste mätningen med linjebredd vid halva höjden, och arean under kurvan.

    Halva höjden räknas från noll (mörkeravdragna counts). FWHM av en smal linje (laser, Hg 546 nm) är instrumentets
    upplösning, inte källans bredd (Krav 19b, 20). Arean är relativ uteffekt, aldrig watt.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: fwhm tar högst ett ord (N)")
    n = registry.to_int("N", args[0], 1) if args else 5
    spectrum, values = latest(state)
    x_unit, area_unit = units(spectrum)
    found = peaks.find_peaks(spectrum["x"], values, spectrum["mask"])[:n]
    if not found:
        out.say("inga toppar")
    for k, i in enumerate(found, start=1):
        where, height, width = summary(spectrum, values, i)
        text = f"{out.fmt(width)} {x_unit}" if np.isfinite(width) else "okänd (kurvan når inte halva höjden)"
        out.say(f"topp {k}: {out.fmt(where)} {x_unit}, höjd {out.fmt(height)}, FWHM {text}")
    out.say(f"area: {out.fmt(peaks.area(spectrum['x'], values, spectrum['mask']))} {area_unit} (relativ, inte watt)")
    out.say("FWHM av en smal linje (laser, Hg) är instrumentets upplösning, inte källans bredd.")


NORM_LABEL = "normerad signal (relativ, bara visning)"


def load_curves(folders):
    """Mätmapparna som [(spektrum, namn)]; namnet är note ur settings.json, annars mappens namn.

    Fel: ValueError med input.invalid_argument när mapparna har olika enheter; fel ur files.load_measurement.
    """
    spectra = [files.load_measurement(folder) for folder in folders]
    if len({(s["x_label"], s["y_label"]) for s in spectra}) > 1:
        raise ValueError("input.invalid_argument: mapparna har olika enheter (pixel eller nm; counts, relativ eller kvot)")
    return [(s, s["settings"].get("note") or Path(s["folder"]).name) for s in spectra]


def normalized(values, name):
    """values delad med sitt största giltiga värde, bara för visning. Fel: ValueError om det största värdet inte är över 0."""
    top = np.nanmax(values) if np.any(np.isfinite(values)) else 0.0
    if top <= 0:
        raise ValueError(f"input.invalid_argument: {name} går inte att normera, största värdet är {top:g}")
    return values / top


def _row(spectrum, values):
    """En rad i compare: den högsta toppens läge, höjd och FWHM, och arean."""
    x_unit, area_unit = units(spectrum)
    area = f"area {out.fmt(peaks.area(spectrum['x'], values, spectrum['mask']))} {area_unit}"
    found = peaks.find_peaks(spectrum["x"], values, spectrum["mask"])
    if not found:
        return f"ingen topp, {area}"
    where, height, width = summary(spectrum, values, found[0])
    return f"topp {out.fmt(where)} {x_unit}, höjd {out.fmt(height)}, FWHM {out.fmt(width)} {x_unit}, {area}"


@registry.command("compare", "MAPP... [--norm]: mätmappar i samma figur, med topp, FWHM och area (--norm: formen)",
                  "compare MAPP... [--norm]")
def cmd_compare(state, args):
    """Kommandot compare MAPP... [--norm]: en rad per mapp och kurvorna i ett fönster (Krav 17a och 17b). Ändrar inte state.

    Utan --norm jämförs nivån: den betyder bara något med samma exponering, gain och respons. Med --norm jämförs formen.
    """
    norm = "--norm" in args
    folders = [word for word in args if word != "--norm"]
    if not folders:
        raise ValueError("input.invalid_argument: compare: MAPP saknas")
    loaded = load_curves(folders)
    curves = []
    for spectrum, name in loaded:
        values = np.where(spectrum["mask"], spectrum["values"], np.nan)
        out.say(f"{name}: {_row(spectrum, values)}")
        curves.append((spectrum["x"], normalized(values, name) if norm else values, name))
    out.say("normerade till sitt max: formen, inte nivån" if norm else "Relativa tal från kameran; inte watt, lumen eller verkningsgrad.")
    first = loaded[0][0]
    out.say("Stäng fönstret (krysset) för att komma tillbaka till prompten.")
    plot.show_spectra(curves, first["x_label"], NORM_LABEL if norm else first["y_label"])


FLAGS = ("--norm", "--log", "--ev")


def _figure_words(args):
    """Orden efter figure som (UT, mapparna, flaggorna, xlim). Fel: ValueError med input.invalid_argument vid fel ord."""
    if not args or not args[0].lower().endswith((".png", ".svg")):
        raise ValueError("input.invalid_argument: figure: första ordet ska vara UT.png eller UT.svg")
    rest, xlim = list(args[1:]), None
    if "--xlim" in rest:
        k = rest.index("--xlim")
        try:
            xlim = (float(rest[k + 1]), float(rest[k + 2]))
        except (IndexError, ValueError) as error:
            raise ValueError("input.invalid_argument: figure: --xlim tar två tal, MIN MAX") from error
        if not (np.all(np.isfinite(xlim)) and xlim[0] < xlim[1]):
            raise ValueError("input.invalid_argument: figure: --xlim MIN MAX ska vara ändliga och MIN mindre än MAX")
        del rest[k:k + 3]
    unknown = [word for word in rest if word.startswith("--") and word not in FLAGS]
    if unknown:
        raise ValueError(f"input.invalid_argument: figure: okänd flagga {unknown[0]}, välj {', '.join(FLAGS)} eller --xlim")
    return args[0], [word for word in rest if word not in FLAGS], {word for word in rest if word in FLAGS}, xlim


def _conditions(spectrum, state):
    """Villkoren till bildtexten: ur settings.json när mätningen är sparad eller laddad, annars ur state (inte sparad)."""
    settings = spectrum.get("settings")
    if settings is None and "saved_in" in spectrum:
        settings = files.load_measurement(spectrum["saved_in"])["settings"]
    if settings is None:
        settings = dict(state["settings"], mode=state["mode"], use_response=state["use_response"], program_version=__version__)
    folder = spectrum.get("folder", spectrum.get("saved_in", "inte sparad"))  # folder: laddad, saved_in: sparad
    return (f"mapp {folder}, mätt {settings.get('measured_at', 'okänt')}, "
            f"kanal {settings.get('channel')}, frames {settings.get('frames')}, läge {settings.get('mode')}, "
            f"respons {'ja' if settings.get('use_response') else 'nej'}, version {settings.get('program_version')}")


@registry.command("figure", "UT.png|UT.svg [MAPP...] [--norm] [--xlim MIN MAX] [--log] [--ev]: rapportfigur och UT.txt till bildtexten",
                  "figure UT.png [MAPP...] [--norm] [--xlim MIN MAX] [--log] [--ev]")
def cmd_figure(state, args):
    """Kommandot figure UT.png|UT.svg: senaste mätningen, eller mapparna i samma axlar, som egen figur till rapporten.

    16 x 9 cm, 200 dpi, axlar med enhet och ingen titel: bildtexten skrivs under figuren i rapporten. UT.txt bredvid
    bilden har villkoren till den. --ev: fotonenergi på x-axeln (kräver nm). Ändrar inte state.
    """
    path, folders, flags, xlim = _figure_words(args)
    if folders:
        loaded = load_curves(folders)
    else:
        loaded = [(latest(state)[0], "senaste mätningen")]
    x_label = loaded[0][0]["x_label"]
    if "--ev" in flags and x_label != "våglängd (nm)":
        raise ValueError("input.invalid_argument: figure --ev kräver våglängd i nm, kör calibrate först")
    curves, lines = [], []
    for spectrum, name in loaded:
        values = np.where(spectrum["mask"], spectrum["values"], np.nan)
        x = bandgap.ev(spectrum["x"]) if "--ev" in flags else spectrum["x"]
        curves.append((x, normalized(values, name) if "--norm" in flags else values, name))
        lines.append(f"{name}: {_conditions(spectrum, state)}")
    x_label = "fotonenergi (eV)" if "--ev" in flags else x_label
    y_label = NORM_LABEL if "--norm" in flags else loaded[0][0]["y_label"]
    plot.save_figure(path, curves, x_label, y_label, xlim, "--log" in flags)
    caption = Path(path).with_suffix(".txt")
    head = f"Figur {Path(path).name}: x {x_label}, y {y_label}" + (", logaritmisk y" if "--log" in flags else "")
    tail = "Relativa tal från kameran; inte watt, lumen eller verkningsgrad."
    caption.write_text("\n".join([head, *lines, tail]) + "\n", encoding="utf-8")
    out.say(f"Sparad: {path} och {caption.as_posix()} (villkoren till bildtexten)")
