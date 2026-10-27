import numpy as np

from spectrometer.core import out

HC = 1239.84
WINDOW_NM = (366.0, 766.0)


def absorbance(transmission, mask):
    a = np.full(transmission.shape, np.nan)
    ok = mask & np.isfinite(transmission) & (transmission > 0)
    a[ok] = -np.log10(transmission[ok])
    return a


def edge(x_nm, absorb, step_nm):
    ok = np.isfinite(absorb)
    order = np.argsort((HC / x_nm)[ok])
    E, A = (HC / x_nm)[ok][order], absorb[ok][order]
    if E.size < 3:
        raise ValueError("too few valid absorbance values")
    slope = np.gradient(A, E)
    i = int(np.nanargmax(slope))
    eg = E[i] - A[i] / slope[i]
    lam = HC / eg
    unc = abs(HC / (lam - 0.5 * step_nm) - HC / (lam + 0.5 * step_nm)) / 2
    return float(eg), float(unc)


def report(x_nm, transmission, mask):
    absorb = absorbance(transmission, mask & (transmission >= 0.05))
    step = float(np.median(np.abs(np.diff(x_nm))))
    with np.errstate(divide="ignore", invalid="ignore"):
        eg, unc = edge(x_nm, absorb, step)
    if not np.isfinite(eg) or eg <= 0:
        raise ValueError("no absorption edge (the absorbance does not rise towards higher energy)")
    lam = HC / eg
    inside = "inside" if WINDOW_NM[0] <= lam <= WINDOW_NM[1] else "outside"
    out.say(f"bandgap: {out.pm(eg, unc, 'eV')}, the edge at {lam:.1f} nm ({inside} the window {WINDOW_NM[0]:g}-{WINDOW_NM[1]:g} nm)")
    valid = x_nm[mask & np.isfinite(transmission)]
    if min(lam - valid.min(), valid.max() - lam) < 30:
        out.warn("the edge is closer than 30 nm to the end of the data, the bandgap may lie outside")
    out.say("the uncertainty is only ±0.5 pixel steps; calibration, reflection and scattering are not included")
