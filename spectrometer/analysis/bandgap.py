"""Bandgap ur ett transmissionsspektrum: eV-axel och absorptionskanten (Krav 22)."""

import numpy as np

HC = 1239.84  # eV·nm


def ev(x_nm):
    """Fotonenergi i eV."""
    return HC / np.asarray(x_nm, dtype=np.float64)


def absorbance(transmission, mask):
    """A = -log10(T) där T > 0 och masken är sann, NaN annars."""
    a = np.full(transmission.shape, np.nan)
    ok = mask & np.isfinite(transmission) & (transmission > 0)
    a[ok] = -np.log10(transmission[ok])
    return a


def edge(x_nm, absorb, step_nm):
    """Absorptionskanten: brantaste lutningen i A mot E, linjen genom den extrapolerad till A = 0.

    Returnerar (E_g_eV, osäkerhet_eV, index). Osäkerheten är ±0,5 pixelsteg omräknat till eV vid kanten.
    """
    E = ev(x_nm)
    ok = np.isfinite(absorb)
    if np.count_nonzero(ok) < 3:
        raise ValueError("input.missing_data: för få giltiga absorbansvärden")
    order = np.argsort(E[ok])
    Eo, Ao = E[ok][order], absorb[ok][order]
    slope = np.gradient(Ao, Eo)
    i = int(np.nanargmax(slope))
    eg = Eo[i] - Ao[i] / slope[i]
    lam = HC / eg
    unc = abs(HC / (lam - 0.5 * step_nm) - HC / (lam + 0.5 * step_nm)) / 2
    return float(eg), float(unc), i


WINDOW_NM = (366.0, 766.0)  # Krav 22: kanten ska ligga här med KO-kalibreringen (3,39–1,62 eV)
EDGE_MARGIN_NM = 30.0  # kanten närmare än så från mätningens kant: varning (ANA-50)
T_MIN = 0.05  # transmission under 5 % räknas inte: där är kvoten mest brus och −log10(T) skenar


def report(x_nm, transmission, mask):
    """Raderna som bandgap skriver ur ett transmissionsspektrum: E_g i eV och nm, fönstret och osäkerheten.

    Brantaste lutningen i A = −log10(T) mot E, extrapolerad till A = 0 (planen; rev7 anpassar två räta linjer),
    bara där T är minst T_MIN.
    En rad som börjar med "Varning: " är en varning. Fel: ValueError med input.missing_data utan en kant.
    """
    absorb = absorbance(transmission, mask & (transmission >= T_MIN))
    step = float(np.median(np.abs(np.diff(x_nm))))
    with np.errstate(divide="ignore", invalid="ignore"):  # platt absorbans: lutningen 0 ger oändligt E_g
        eg, unc, _ = edge(x_nm, absorb, step)
    if not np.isfinite(eg) or eg <= 0:
        raise ValueError("input.missing_data: ingen absorptionskant (absorbansen stiger inte mot högre energi)")
    lam = HC / eg
    low, high = WINDOW_NM
    where = "inne" if low <= lam <= high else "utanför"
    lines = [f"bandgap: {eg:.3f} ± {unc:.3f} eV, kanten vid {lam:.1f} nm",
             f"fönstret {low:g}–{high:g} nm ({HC / low:.2f}–{HC / high:.2f} eV): kanten ligger {where}"]
    valid = x_nm[mask & np.isfinite(transmission)]
    if min(lam - valid.min(), valid.max() - lam) < EDGE_MARGIN_NM:
        lines.append("Varning: kanten ligger närmare än 30 nm från mätningens kant, bandgapet kan ligga utanför")
    lines.append(f"punkter med T under {T_MIN:g} räknas inte: där är kvoten mest brus")
    lines.append("osäkerheten är bara ±0,5 pixelsteg; kalibrering, reflektion och spridning ingår inte")
    return lines
