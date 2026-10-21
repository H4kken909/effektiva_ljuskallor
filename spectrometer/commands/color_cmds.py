"""color och mix: färgen i senaste mätningen (Krav 17b, 19a) och RGB-blandning av tre LED (Krav 19). Relativt.

Resultaten lämnas till panelerna colour och rgb (display.remember); view analysis colour visar dem.
"""

import numpy as np

from spectrometer import calc, display, out, registry
from spectrometer.analysis import color, mapp

GROUP = "analys"  # help.analys visar modulens kommandon


@registry.command("color", "färgen i senaste mätningen: x, y, färgtemperatur och avstånd till varmt och kallt vitt")
def cmd_color(state, args):
    """Kommandot color: x, y, färgtemperatur (CCT och Duv, 1.2.15) och relativ ljusstyrka ur senaste mätningen.

    Kräver kalibrering och response on i mode direct: utan responsen är det kamerans färg, inte ljusets.

    Fel: ValueError med input.missing_data utan mätning, kalibrering eller respons, eller utan ljus 380–780 nm.
    """
    registry.need(args, (), "color")
    spectrum = registry.need_spectrum(state)
    if state["coefficients"] is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    if not state["use_response"] or state["mode"] != "direct":
        raise ValueError("input.missing_data: color kräver response on i mode direct (annars är det kamerans färg)")
    out.say_all(color.report(spectrum["x"], spectrum["values"], spectrum["mask"]))
    x, y = color.xy(*color.xyz(spectrum["x"], spectrum["values"], spectrum["mask"]))
    cct, duv, limit = color.cct_duv(x, y)
    meaningful = not limit and abs(duv) <= color.DUV_MAX
    display.remember(state, "colour", {"xy": (x, y), "cct": cct if meaningful else None, "duv": duv,
                                       "locus": color.locus()[1:], "planck": color.planck_locus()[1:]})


SAME = ("roi", "channel", "axis", "frames", "coefficients")  # ska vara lika i de tre LED-mätningarna


def _setting(led, key):
    """Inställningen key i en sparad mätning som text; roi full (null) blir hela bildens yta ur image_size."""
    value = led["settings"].get(key)
    if key == "roi" and value is None and led["settings"].get("image_size"):
        width, height = led["settings"]["image_size"]
        value = [0, 0, width, height]
    return str(value)


def _target(words):
    """Målfärgen (x, y) ur två ord."""
    x, y = registry.to_float("X", words[0], 0), registry.to_float("Y", words[1], 0)
    if x + y >= 1:
        raise ValueError("input.invalid_argument: X + Y ska vara mindre än 1")
    return x, y


def _blend(primaries, target):
    """--target och --cct: vikterna och blandningens färg, eller att tre LED inte räcker (negativ vikt).

    Ger vikterna och blandningens (x, y) (None när en vikt är negativ) till rgb-panelen.
    """
    w = color.weights(primaries, target)
    out.say(f"vikter (relativa, största 1): R {w[0]:.3f}  G {w[1]:.3f}  B {w[2]:.3f}")
    if np.any(w < 0):
        out.warn("negativ vikt: målet ligger utanför triangeln, de tre LED:erna räcker inte")
        return {"weights": w, "blend": None}
    x, y = color.xy(*(primaries @ w))
    out.say(f"blandningen: x {x:.4f}  y {y:.4f}")
    out.say(color.cct_line(x, y))
    return {"weights": w, "blend": (x, y)}


def _sweep(primaries):
    """--sweep: vikterna för varje färg i color.TARGETS och om tre LED räcker (ingen negativ vikt).

    Ger [(namn, x, y, räcker)] till rgb-panelen.
    """
    out.say("färg        x       y       R       G       B       räcker")
    found = []
    for name, (x, y) in color.TARGETS.items():
        w = color.weights(primaries, (x, y))
        enough = bool(np.all(w >= 0))
        out.say(f"{name:<11} {x:.4f}  {y:.4f}  {w[0]:6.3f}  {w[1]:6.3f}  {w[2]:6.3f}  {out.YES[enough]}")
        found.append((name, x, y, enough))
    return found


def _widths(leds, corners, fwhm):
    """--fwhm W: triangeln i xy för de mätta LED:erna och för gaussiska LED med samma toppar och bredden W nm."""
    lam = np.arange(380.0, 781.0)
    tops = [float(led["x"][np.nanargmax(calc.masked_values(led))]) for led in leds]
    model = [color.xy(*color.xyz(lam, color.gaussian(lam, top, fwhm), np.ones(lam.size, dtype=bool))) for top in tops]
    out.say("toppar: " + ", ".join(f"{name} {top:.1f} nm" for name, top in zip("RGB", tops)))
    out.say(f"täckt område i xy: mätta {color.triangle_area(corners):.4f}, "
            f"gaussiska med FWHM {fwhm:g} nm {color.triangle_area(model):.4f}")


@registry.command("mix",
                  "R G B --target X Y | --cct K | --sweep | --fwhm W: blanda tre sparade LED-mätningar till en färg",
                  "mix MAPP_R MAPP_G MAPP_B --target X Y, --cct K, --sweep eller --fwhm W")
def cmd_mix(state, args):
    """Kommandot mix MAPP_R MAPP_G MAPP_B och ett val: vikterna som blandar tre LED-mätningar till en färg (Krav 19).

    --target X Y: färgen (x, y). --cct K: punkten på svartkroppskurvan vid K kelvin. --sweep: tabell för sex färger
    och SUB1:s två vitpunkter. --fwhm W: triangeln i xy med gaussiska LED, bredd W nm (Krav 19b). Vikt 1 är LED:n
    som den mättes; relativt, aldrig watt. Mätningarna sparas med response on och samma inställningar.

    Fel: ValueError med input.invalid_argument vid fel ord, med input.missing_data om en mätning inte duger;
    OSError om en mapp saknas.
    """
    if len(args) < 4:
        raise ValueError("input.invalid_argument: mix: tre mätmappar och --target X Y, --cct K, --sweep eller --fwhm W")
    folders, option, rest = args[:3], args[3], args[4:]
    leds = [mapp.read_required(folder, "direct") for folder in folders]  # kalibrerade och responskorrigerade
    differ = [key for key in SAME if len({_setting(led, key) for led in leds}) > 1]
    if differ:
        out.warn(f"mätningarna skiljer sig i {', '.join(differ)}; vikterna jämför då olika saker")
    primaries = np.array([color.xyz(led["x"], led["values"], led["mask"]) for led in leds]).T  # en kolumn per LED
    corners = [color.xy(*primaries[:, k]) for k in range(3)]
    for name, (x, y) in zip("RGB", corners):
        out.say(f"{name}: x {x:.4f}  y {y:.4f}")
    result = {"corners": corners, "locus": color.locus()[1:]}  # till rgb-panelen
    if option == "--target":
        registry.need(rest, ("X", "Y"), "mix --target")
        result.update(_blend(primaries, _target(rest)))
    elif option == "--cct":
        registry.need(rest, ("K",), "mix --cct")
        target = color.planck_xy(registry.to_float("K", rest[0], 0))
        out.say(f"mål: svartkroppskurvan vid {rest[0]} K, x {target[0]:.4f}  y {target[1]:.4f}")
        result.update(_blend(primaries, target))
    elif option == "--sweep":
        registry.need(rest, (), "mix --sweep")
        result["targets"] = _sweep(primaries)
    elif option == "--fwhm":
        registry.need(rest, ("W",), "mix --fwhm")
        _widths(leds, corners, registry.to_float("W", rest[0], 0))
    else:
        raise ValueError(f"input.invalid_argument: mix: okänt val {option}, välj --target, --cct, --sweep eller --fwhm")
    display.remember(state, "rgb", result)
