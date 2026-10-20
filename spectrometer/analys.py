"""Analysskriptet: kommandon på sparade mätmappar, utan prompten och utan kamera (R55).

python -m spectrometer.analys KOMMANDO MAPP [val]. Läser bara; skriver aldrig i mätmappen. Slutkoden är 0 när det
gick, 1 vid fel (raden Fel: skrivs) och 2 vid okänt eller saknat kommando (listan skrivs).
"""

import sys

import numpy as np

from spectrometer import out, peaks, registry
from spectrometer.analysis import bandgap, color, mapp

PEAK_MIN = 0.10  # toppar: standardtröskeln, andel av största värdet (samma som toppar i prompten)
PEAK_DISTANCE = 3  # toppar närmare än så (positioner) slås ihop till den högsta


def _folder_and_options(args, allowed):
    """MAPP och valen efter den: ["MAPP", "--min", "0.2"] ger ("MAPP", {"--min": "0.2"}).

    Fel: ValueError med input.invalid_argument om MAPP saknas, ett val är okänt eller saknar sitt värde.
    """
    if not args:
        raise ValueError("input.invalid_argument: MAPP saknas")
    options, rest = {}, args[1:]
    if len(rest) % 2:
        raise ValueError(f"input.invalid_argument: {rest[-1]} saknar sitt värde")
    for name, value in zip(rest[::2], rest[1::2]):
        if name not in allowed:
            raise ValueError(f"input.invalid_argument: okänt val {name}")
        options[name] = value
    return args[0], options


def _top_peaks(saved, fraction, count):
    """De count högsta topparna som (x, värde), högst först; tröskeln är fraction av största giltiga värdet."""
    if not saved["mask"].any():
        return []
    values = np.where(saved["mask"], saved["values"], np.nan)
    found = peaks.find_peaks(saved["values"], saved["mask"], fraction * np.nanmax(values), PEAK_DISTANCE)[:count]
    index = np.arange(values.size)
    return [(float(np.interp(peaks.refine_peak(values, i), index, saved["x"])), float(values[i])) for i in found]


def cmd_sammanfatta(args):
    """sammanfatta MAPP: snabbkoll efter save; mättid, läge, enhet, giltiga, max, bilder, mättnad och toppar."""
    folder, _options = _folder_and_options(args, ())
    saved = mapp.read(folder)
    settings, mask = saved["settings"], saved["mask"]
    unit = "nm" if saved["x_label"] == "nm" else "pixel"
    out.say(f"mapp: {saved['folder']}")
    out.say(f"mättid: {settings.get('measured_at', 'okänd')}")
    out.say(f"läge: {settings.get('mode', 'okänt')}, enhet: {mapp.unit(settings)}, "
            f"kalibrerad: {'ja' if unit == 'nm' else 'nej'}")
    out.say(f"giltiga: {np.count_nonzero(mask)} av {mask.size} positioner")
    if mask.any():
        i = int(np.nanargmax(np.where(mask, saved["values"], np.nan)))
        out.say(f"max: {out.fmt(saved['values'][i])} vid {unit} {out.fmt(saved['x'][i])}")
    out.say(f"bilder: {settings.get('frames', 'okänt')}, mättade pixlar: {settings.get('saturated_px', 'okänt')}")
    tops = ", ".join(f"{unit} {x:.1f} ({out.fmt(value)})" for x, value in _top_peaks(saved, PEAK_MIN, 3))
    out.say(f"toppar: {tops or 'inga'}")
    out.say("Relativa tal från kameran.")


def cmd_toppar(args):
    """toppar MAPP [--min F] [--antal N]: topparna i en sparad mätning, högst först (som toppar i prompten)."""
    folder, options = _folder_and_options(args, ("--min", "--antal"))
    fraction = registry.to_float("F", options.get("--min", str(PEAK_MIN)), 0)
    count = registry.to_int("N", options.get("--antal", "10"), 1)
    saved = mapp.read(folder)
    unit = "nm" if saved["x_label"] == "nm" else "pixel"
    out.say(f"toppar i {saved['folder']}: över {100 * fraction:g} % av största värdet")
    found = _top_peaks(saved, fraction, count)
    if not found:
        out.say("inga toppar")
    for k, (x, value) in enumerate(found, start=1):
        out.say(f"topp {k}: {unit} {x:.1f}  värde {out.fmt(value)}")


def cmd_farg(args):
    """farg MAPP: färgen i en sparad mätning, som color i prompten (sparad med response on i mode direct)."""
    folder, _options = _folder_and_options(args, ())
    saved = mapp.read(folder)
    mapp.require(saved, "direct")
    out.say_all(color.report(saved["x"], saved["values"], saved["mask"]))


def cmd_kant(args):
    """kant MAPP: bandgapet ur en sparad transmissionsmätning, som bandgap MAPP i prompten (Krav 22)."""
    folder, _options = _folder_and_options(args, ())
    saved = mapp.read(folder)
    mapp.require(saved, "transmission")
    out.say_all(bandgap.report(saved["x"], saved["values"], saved["mask"]))


KOMMANDON = {"sammanfatta": cmd_sammanfatta, "toppar": cmd_toppar, "farg": cmd_farg, "kant": cmd_kant}


def main(argv=None):
    """Kör ett kommando ur KOMMANDON. argv: orden efter programnamnet, None läser sys.argv.

    Returnerar slutkoden: 0 när det gick, 1 vid fel (Fel: skrivs), 2 vid okänt eller saknat kommando (listan skrivs).
    """
    if hasattr(sys.stdout, "reconfigure"):  # som main: samma bytes på Windows och Arch
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:] if argv is None else list(argv)
    if not args or args[0] not in KOMMANDON:
        if args:
            out.error(f"input.invalid_argument: okänt kommando {args[0]}")
        out.say("Användning: python -m spectrometer.analys KOMMANDO MAPP [val]")
        for func in KOMMANDON.values():
            out.say(f"  {func.__doc__.splitlines()[0]}")
        return 2
    try:
        KOMMANDON[args[0]](args[1:])
    except (ValueError, OSError) as error:
        out.error(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
