"""bandgap: bandgapet i eV ur absorptionskanten i en transmissionsmätning (Krav 22)."""

from spectrometer import out, registry
from spectrometer.analysis import bandgap, mapp


def _transmission(state, args):
    """(x i nm, transmission, mask) ur mätmappen args[0], eller ur senaste mätningen i mode transmission.

    Fel: ValueError med input.missing_data utan mätning, kalibrering eller transmission.
    """
    if args:
        saved = mapp.read(args[0])
        mapp.require(saved, "transmission")  # samma kontroll som analysskriptet
        return saved["x"], saved["values"], saved["mask"]
    spectrum = state["spectrum"]
    if spectrum is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step först.")
    if state["coefficients"] is None:
        raise ValueError("input.missing_data: ingen kalibrering, kör calibrate först")
    if state["mode"] != "transmission":
        raise ValueError("input.missing_data: bandgap kräver mode transmission (provet delat med referensen)")
    return spectrum["x"], spectrum["values"], spectrum["mask"]


@registry.command("bandgap", "[MAPP]: bandgap i eV ur absorptionskanten i senaste transmissionsmätningen eller i MAPP",
                  "bandgap [MAPP]")
def cmd_bandgap(state, args):
    """Kommandot bandgap [MAPP]: E_g i eV och nm, om kanten ligger i fönstret 366–766 nm, och osäkerheten.

    A = −log10(T) och E = 1239,84/λ; brantaste lutningen i A mot E, extrapolerad till A = 0, ger E_g. Osäkerheten
    är ±0,5 pixelsteg omräknat till eV; kalibrering, reflektion och spridning ingår inte.

    Fel: ValueError med input.invalid_argument vid fler ord, med input.missing_data utan transmissionsmätning eller
    utan kant; OSError om MAPP saknas.
    """
    if len(args) > 1:
        raise ValueError("input.invalid_argument: bandgap tar högst ett ord (MAPP)")
    out.say_all(bandgap.report(*_transmission(state, args)))
