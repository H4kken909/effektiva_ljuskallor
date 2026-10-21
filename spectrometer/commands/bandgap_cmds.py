"""bandgap: bandgapet i eV ur absorptionskanten i en transmissionsmätning (Krav 22)."""

from spectrometer import display, out, registry
from spectrometer.analysis import bandgap, mapp

GROUP = "analys"  # help.analys visar modulens kommandon


def _transmission(state, args):
    """(x i nm, transmission, mask) ur mätmappen args[0], eller ur senaste mätningen i mode transmission."""
    if args:
        saved = mapp.read_required(args[0], "transmission")
        return saved["x"], saved["values"], saved["mask"]
    spectrum = registry.need_spectrum(state)
    if state["coefficients"] is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    if state["mode"] != "transmission":
        raise ValueError("input.missing_data: bandgap kräver mode transmission (provet delat med referensen)")
    return spectrum["x"], spectrum["values"], spectrum["mask"]


@registry.command("bandgap", "[MAPP] [--anpassa]: bandgap i eV ur absorptionskanten i senaste transmissionsmätningen "
                  "eller i MAPP (--anpassa: två räta linjer)", "bandgap [MAPP] [--anpassa]")
def cmd_bandgap(state, args):
    """Kommandot bandgap [MAPP] [--anpassa]: E_g i eV och nm, om kanten ligger i fönstret 366–766 nm, och osäkerheten.

    A = −log10(T) och E = 1239,84/λ. Utan --anpassa: brantaste lutningen i A mot E, extrapolerad till A = 0; osäkerheten
    är ±0,5 pixelsteg omräknat till eV. Med --anpassa: två sammanhängande räta linjer med brytpunkt, som rev7,
    med 3-standardfelsregeln och ändpunktskontrollen. Kalibrering, reflektion och spridning ingår inte.

    Fel: ValueError med input.invalid_argument vid fler ord, med input.missing_data utan transmissionsmätning eller
    utan kant; som load när MAPP inte är en mätmapp.
    """
    fit = "--anpassa" in args
    words = [word for word in args if word != "--anpassa"]
    registry.at_most_one(words, "bandgap", "MAPP")
    report = bandgap.fit_report if fit else bandgap.report
    x, values, mask = _transmission(state, words)
    out.say_all(report(x, values, mask))
    E, A, line, eg = bandgap.edge_lines(x, values, mask, fit)  # till edge-panelen (view analysis edge)
    point = (line[0][1], line[1][1]) if fit else (eg, 0.0)  # brytpunkten, eller där linjen når A = 0
    display.remember(state, "edge", {"E": E, "A": A, "line": line, "eg": eg, "nm": bandgap.HC / eg, "point": point,
                                     "method": "två räta linjer" if fit else "brantaste lutningen"})
