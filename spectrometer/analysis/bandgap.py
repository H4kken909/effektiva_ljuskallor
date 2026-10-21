"""Bandgap ur ett transmissionsspektrum: eV-axel och absorptionskanten (Krav 22)."""

import numpy as np

from spectrometer import out

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


def _by_energy(x_nm, absorb):
    """(E, A) för de giltiga punkterna (A är ändlig), stigande i E."""
    ok = np.isfinite(absorb)
    E = ev(x_nm)[ok]
    order = np.argsort(E)
    return E[order], absorb[ok][order]


def edge(x_nm, absorb, step_nm):
    """Absorptionskanten: brantaste lutningen i A mot E, linjen genom den extrapolerad till A = 0.

    Returnerar (E_g_eV, osäkerhet_eV, index). Osäkerheten är ±0,5 pixelsteg omräknat till eV vid kanten.
    """
    Eo, Ao = _by_energy(x_nm, absorb)
    if Eo.size < 3:
        raise ValueError("input.missing_data: för få giltiga absorbansvärden")
    slope = np.gradient(Ao, Eo)
    i = int(np.nanargmax(slope))
    eg = Eo[i] - Ao[i] / slope[i]
    lam = HC / eg
    unc = abs(HC / (lam - 0.5 * step_nm) - HC / (lam + 0.5 * step_nm)) / 2
    return float(eg), float(unc), i


WINDOW_NM = (366.0, 766.0)  # Krav 22: kanten ska ligga här med KO-kalibreringen (3,39–1,62 eV)
EDGE_MARGIN_NM = 30.0  # kanten närmare än så från mätningens kant: varning
T_MIN = 0.05  # transmission under 5 % räknas inte: där är kvoten mest brus och −log10(T) skenar
MIN_RISE = 0.1  # så mycket ska absorbansen stiga från låg till hög energi för en kant (T faller till ca 80 %)
END_SHARE = 0.05  # andelen giltiga punkter i var ände (minst 3) som rise jämför


def rise(x_nm, absorb):
    """Hur mycket absorbansen stiger över mätningen: medianen i högenergiänden minus medianen i lågenergiänden.

    Ändarna är END_SHARE av de giltiga punkterna (minst 3), sorterade efter energi. Brus kring en platt T (T ≈ 1)
    ger nära 0, en verklig kant tiondelar eller mer. Medianen gör att enstaka brusiga punkter inte räcker.
    """
    A = _by_energy(x_nm, absorb)[1]
    k = max(3, round(END_SHARE * A.size))
    return float(np.median(A[-k:]) - np.median(A[:k]))


def _require_rise(x_nm, absorb):
    """Fel (input.missing_data) när absorbansen inte stiger minst MIN_RISE från låg till hög energi (rise)."""
    gain = rise(x_nm, absorb)
    if gain < MIN_RISE:  # brus kring T ≈ 1 gav förut ett värde (2,03 eV), nu ingen kant
        raise ValueError(f"input.missing_data: ingen absorptionskant: absorbansen stiger bara {gain:.3f} från lägsta "
                         f"till högsta energin, minst {MIN_RISE:g} behövs (T ska falla under ca 80 %)")


def _find_edge(x_nm, transmission, mask):
    """Absorbansen (bara där T är minst T_MIN) och kanten ur edge: (absorbansen, E_g i eV, osäkerhet i eV, index)."""
    absorb = absorbance(transmission, mask & (transmission >= T_MIN))
    step = float(np.median(np.abs(np.diff(x_nm))))
    with np.errstate(divide="ignore", invalid="ignore"):  # platt absorbans: lutningen 0 ger oändligt E_g
        eg, unc, i = edge(x_nm, absorb, step)
    return absorb, eg, unc, i


def _edge_notes(lam, x_nm, transmission, mask):
    """Raderna om kantens läge som report och fit_report delar: fönstret, varning nära mätningens kant, T_MIN."""
    low, high = WINDOW_NM
    where = "inne" if low <= lam <= high else "utanför"
    lines = [f"fönstret {low:g}–{high:g} nm ({HC / low:.2f}–{HC / high:.2f} eV): kanten ligger {where}"]
    valid = x_nm[mask & np.isfinite(transmission)]
    if min(lam - valid.min(), valid.max() - lam) < EDGE_MARGIN_NM:
        lines.append("Varning: kanten ligger närmare än 30 nm från mätningens kant, bandgapet kan ligga utanför")
    lines.append(f"punkter med T under {T_MIN:g} räknas inte: där är kvoten mest brus")
    return lines


def report(x_nm, transmission, mask):
    """Raderna som bandgap skriver ur ett transmissionsspektrum: E_g i eV och nm, fönstret och osäkerheten.

    Brantaste lutningen i A = −log10(T) mot E, extrapolerad till A = 0, bara där T är minst T_MIN (rev7 anpassar två
    räta linjer, se fit_report). En rad som börjar med "Varning: " är en varning.
    """
    absorb, eg, unc, _ = _find_edge(x_nm, transmission, mask)
    if not np.isfinite(eg) or eg <= 0:
        raise ValueError("input.missing_data: ingen absorptionskant (absorbansen stiger inte mot högre energi)")
    _require_rise(x_nm, absorb)
    lam = HC / eg
    return [f"bandgap: {out.pm(eg, unc, 'eV')}, kanten vid {lam:.1f} nm",  # avrundat efter osäkerheten
            *_edge_notes(lam, x_nm, transmission, mask),
            "osäkerheten är bara ±0,5 pixelsteg; kalibrering, reflektion och spridning ingår inte"]


MIN_POINTS = 8  # rev7: minst åtta punkter i anpassningen med två räta linjer
SIDE_POINTS = 3  # rev7: minst tre punkter på var sida om brytpunkten
SE_RULE = 3.0  # rev7: lutningsökningen ska vara större än tre uppskattade standardfel (en brusregel, inget bevis)


def longest_run(ok):
    """Indexen i det längsta sammanhängande intervallet där ok är sant (rev7: ett sammanhängande giltigt intervall)."""
    best, start = (0, 0), None
    for k, flag in enumerate(np.append(ok, False)):
        if flag and start is None:
            start = k
        elif not flag and start is not None:
            if k - start > best[1] - best[0]:
                best = (start, k)
            start = None
    return np.arange(*best)


def _hinge(E, A, ec):
    """A = a + b·(E − ec) + d·max(0, E − ec) med minsta kvadrat vid fast ec: ((a, b, d), kvadratsumman, X)."""
    X = np.column_stack([np.ones_like(E), E - ec, np.maximum(0.0, E - ec)])
    p = np.linalg.lstsq(X, A, rcond=None)[0]
    r = A - X @ p
    return p, float(r @ r), X


def two_lines(E, A):
    """Två sammanhängande räta linjer i A mot E med brytpunkten i en mätpunkt (rev7). E stigande.

    Varje punkt med minst SIDE_POINTS punkter på var sida provas som brytpunkt ec. En kandidat måste ha d > 0 (brantare
    efter brytpunkten) och b + d > 0 (absorbansen stiger efter den); den med minst kvadratsumma vinner.
    Ger en ordbok: ec, index, a, b, d, se_d ur s²·(XᵀX)⁻¹ med s² = SSE/(n − 3), och se_ec ur samma modell med ec som
    fjärde parameter (Jacobianen, s² = SSE/(n − 4)).
    """
    best = None
    for k in range(SIDE_POINTS, E.size - SIDE_POINTS):
        p, sse, X = _hinge(E, A, E[k])
        if p[2] > 0 and p[1] + p[2] > 0 and (best is None or sse < best[1]):
            best = (k, sse, p, X)
    if best is None:
        raise ValueError("input.missing_data: ingen absorptionskant: ingen brytpunkt där absorbansen blir brantare")
    k, sse, p, X = best
    n = E.size
    se_d = float(np.sqrt(sse / (n - 3) * np.linalg.pinv(X.T @ X)[2, 2]))
    J = np.column_stack([X, -(p[1] + p[2] * (E > E[k]))])  # A:s derivata mot ec
    se_ec = float(np.sqrt(sse / (n - 4) * np.linalg.pinv(J.T @ J)[3, 3]))
    return {"ec": float(E[k]), "index": k, "a": float(p[0]), "b": float(p[1]), "d": float(p[2]), "se_d": se_d,
            "se_ec": se_ec}


def fit_points(x_nm, transmission, mask):
    """(E, A) stigande i E för två räta linjer: det längsta sammanhängande intervallet med T minst T_MIN."""
    run = longest_run(mask & np.isfinite(transmission) & (transmission >= T_MIN))
    if run.size < MIN_POINTS:
        raise ValueError(f"input.missing_data: för få punkter för två räta linjer ({run.size}, minst {MIN_POINTS})")
    E, A = ev(x_nm[run]), -np.log10(transmission[run])
    _require_rise(x_nm[run], A)
    order = np.argsort(E)
    return E[order], A[order]


def fit_report(x_nm, transmission, mask):
    """Raderna som bandgap --anpassa skriver: brytpunkten mellan två räta linjer (rev7).

    Kanten avvisas (ingen kant) när lutningsökningen d är mindre än SE_RULE standardfel eller när brytpunkten hamnar
    vid intervallets gräns. Ändpunktskontrollen anpassar igen utan första och utan sista punkten (rev7 steg 5).
    En rad som börjar med "Varning: " är en varning.
    """
    E, A = fit_points(x_nm, transmission, mask)
    fit = two_lines(E, A)
    ratio = fit["d"] / fit["se_d"] if fit["se_d"] > 0 else float("inf")
    if ratio < SE_RULE:
        raise ValueError(f"input.missing_data: ingen absorptionskant: lutningsökningen är {ratio:.1f} standardfel, "
                         f"minst {SE_RULE:g} behövs")
    if fit["index"] in (SIDE_POINTS, E.size - SIDE_POINTS - 1):
        raise ValueError("input.missing_data: ingen absorptionskant: brytpunkten ligger vid intervallets gräns")
    try:
        ends = [two_lines(E[1:], A[1:])["ec"], two_lines(E[:-1], A[:-1])["ec"]]
        check = (f"ändpunktskontroll: utan första punkten {ends[0]:.3f} eV, utan sista {ends[1]:.3f} eV "
                 f"(ändring högst {max(abs(e - fit['ec']) for e in ends):.3f} eV)")
    except ValueError:
        check = "Varning: ändpunktskontrollen hittar ingen brytpunkt utan första eller sista punkten"
    lam = HC / fit["ec"]
    noise = f"{ratio:.0f} standardfel" if np.isfinite(ratio) else "utan brus"
    return [f"bandgap (två räta linjer): {out.pm(fit['ec'], fit['se_ec'], 'eV')}, brytpunkten vid {lam:.1f} nm",
            f"lutningsökning d: {out.pm(fit['d'], fit['se_d'])} per eV ({noise}, minst {SE_RULE:g}), {E.size} punkter",
            check,
            *_edge_notes(lam, x_nm, transmission, mask),
            "± är anpassningsfelet; empirisk uppskattning: reflektion, spridning och kalibreringsfel ingår inte"]


def edge_lines(x_nm, transmission, mask, fit=False):
    """Absorbansen mot energin och kanten som report eller fit_report (fit) fann, till edge-panelen.

    Ger (E, A, (E_linje, A_linje), E_g) med E stigande: med fit de två räta linjerna, annars linjen genom brantaste
    punkten från A = 0 upp till största absorbansen. Samma räkning som utskriften; panelen räknar inget själv.
    """
    if fit:
        E, A = fit_points(x_nm, transmission, mask)
        lines = two_lines(E, A)
        line_E = np.array([E[0], lines["ec"], E[-1]])
        line_A = lines["a"] + lines["b"] * (line_E - lines["ec"]) + lines["d"] * np.maximum(0.0, line_E - lines["ec"])
        return E, A, (line_E, line_A), lines["ec"]
    absorb, eg, _unc, i = _find_edge(x_nm, transmission, mask)
    E, A = _by_energy(x_nm, absorb)  # samma ordning som i edge, så i pekar på samma punkt
    line_E = np.array([eg, eg + np.max(A) * (E[i] - eg) / A[i]])  # från A = 0 upp till största absorbansen
    return E, A, (line_E, A[i] * (line_E - eg) / (E[i] - eg)), eg
