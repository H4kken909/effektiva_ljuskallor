"""1.2.9 Bandgap: absorptionskanten ur transmissionen, eV, fönstret 366–766 nm och kommandot bandgap (Krav 22)."""

import json

import numpy as np
from test_elias import error_text, new_state

from spectrometer import registry

X = np.arange(400.0, 700.1, 1.5)  # nm, kalibrering 400 nm + 1,5 nm/pixel


def edge_at(center):
    """Transmission som faller brant mot kortare våglängd vid center nm (låg T = absorberat)."""
    return 1 / (1 + np.exp((X - center) / -4))


def transmission_state(values):
    """State med kalibrering och en mätning i mode transmission."""
    state = new_state()
    state["coefficients"] = np.array([400.0, 1.5])
    state["mode"] = "transmission"
    state["spectrum"] = {"x": X, "values": values, "mask": np.isfinite(values)}
    return state


def run(capsys, state, line):
    """Kör en rad och ger raderna som skrevs."""
    registry.run_command(state, line)
    return capsys.readouterr().out.splitlines()


EXPECTED_550 = [
    "bandgap: 2.248 ± 0.003 eV, kanten vid 551.5 nm",
    "fönstret 366–766 nm (3.39–1.62 eV): kanten ligger inne",
    "punkter med T under 0.05 räknas inte: där är kvoten mest brus",
    "osäkerheten är bara ±0,5 pixelsteg; kalibrering, reflektion och spridning ingår inte",
]


def test_bandgap_of_the_latest_measurement(capsys):
    """KRV-29 och KRV-30: kanten vid 550 nm ger ca 2,25 eV (1239,84/550 = 2,254), inne i fönstret."""
    assert run(capsys, transmission_state(edge_at(550)), "bandgap") == EXPECTED_550


def test_bandgap_with_noise_stays_within_002_ev(capsys):
    """Som ANA-56: brus 1 % i T med fast frö flyttar kanten mindre än 0,02 eV (T under 0,05 räknas inte)."""
    rng = np.random.default_rng(1)
    noisy = edge_at(550) + rng.normal(0, 0.01, X.size)
    eg = float(run(capsys, transmission_state(noisy), "bandgap")[0].split()[1])
    assert abs(eg - 1239.84 / 550) < 0.02


def test_bandgap_from_a_saved_folder(tmp_path, capsys):
    """bandgap MAPP läser spectrum.csv och settings.json (mode transmission) och ger samma rader."""
    folder = tmp_path / "prov"
    folder.mkdir()
    rows = ["x_nm,value,valid,absorbance"] + [f"{x:g},{t:.10g},true,{-np.log10(t):.10g}" for x, t in zip(X, edge_at(550))]
    (folder / "spectrum.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (folder / "settings.json").write_text(json.dumps({"mode": "transmission"}), encoding="utf-8")
    assert run(capsys, new_state(), f"bandgap {folder.as_posix()}") == EXPECTED_550
    (folder / "settings.json").write_text(json.dumps({"mode": "direct"}), encoding="utf-8")
    assert error_text(new_state(), f"bandgap {folder.as_posix()}") == (
        f"input.missing_data: {folder.as_posix()}: inte en transmissionsmätning (mode transmission)"
    )


def test_bandgap_warns_near_the_edge_of_the_measurement(capsys):
    """ANA-50: kanten vid 410 nm ligger 10 nm från mätningens början, så bandgapet kan ligga utanför."""
    rows = run(capsys, transmission_state(edge_at(410)), "bandgap")
    assert "Varning: kanten ligger närmare än 30 nm från mätningens kant, bandgapet kan ligga utanför" in rows


def test_bandgap_refuses():
    assert error_text(new_state(), "bandgap") == "input.missing_data: Ingen mätning än. Kör step först."
    state = transmission_state(edge_at(550))
    state["mode"] = "direct"
    assert error_text(state, "bandgap") == (
        "input.missing_data: bandgap kräver mode transmission (provet delat med referensen)"
    )
    assert error_text(transmission_state(np.full(X.size, 0.5)), "bandgap") == (
        "input.missing_data: ingen absorptionskant (absorbansen stiger inte mot högre energi)"
    )
    assert error_text(state, "bandgap a b") == "input.invalid_argument: bandgap tar högst ett ord (MAPP)"
