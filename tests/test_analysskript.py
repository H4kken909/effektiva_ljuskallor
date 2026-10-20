"""1.2.12 Analysskriptet: python -m spectrometer.analys på sparade mätmappar, slutkoderna och analysis.MODULER."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from test_bandgap import EXPECTED_550, X, edge_at
from test_blandning import led
from test_elias import new_state

from spectrometer import analys, analysis, registry
from spectrometer.analysis import color, mapp

ROT = Path(__file__).resolve().parents[1]


def saved_lines(tmp_path):
    """En mätning sparad av programmet: linjer i pixel 5 (80) och 12 (200, grannarna 100). Ger mappen."""
    picture = np.zeros((10, 20, 3), dtype="uint8")
    picture[:, 5], picture[:, 11], picture[:, 12], picture[:, 13] = 80, 100, 200, 100
    cv2.imwrite(str(tmp_path / "linjer.png"), picture)
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in (f"source file {(tmp_path / 'linjer.png').as_posix()}", "step", "save"):
        registry.run_command(state, line)
    return state["spectrum"]["saved_in"]


def run(capsys, args):
    """analys.main(args) och raderna som skrevs: (slutkod, rader)."""
    capsys.readouterr()
    code = analys.main(args)
    return code, capsys.readouterr().out.splitlines()


def test_toppar_on_a_saved_folder(tmp_path, capsys):
    """KAL-10 och ANA-05: samma toppsökning som i prompten, på spectrum.csv; tröskeln skrivs alltid."""
    folder = saved_lines(tmp_path)
    assert run(capsys, ["toppar", folder]) == (0, [
        f"toppar i {folder}: över 10 % av största värdet",
        "topp 1: pixel 12.0  värde 200",
        "topp 2: pixel 5.0  värde 80",
    ])
    assert run(capsys, ["toppar", folder, "--min", "0.5", "--antal", "1"])[1][1:] == ["topp 1: pixel 12.0  värde 200"]


def test_sammanfatta(tmp_path, capsys):
    """ANA-03: snabbkollen efter save, sist att talen är relativa."""
    folder = saved_lines(tmp_path)
    code, rows = run(capsys, ["sammanfatta", folder])
    assert code == 0
    assert rows[0] == f"mapp: {folder}"
    assert rows[2:] == [
        "läge: direct, enhet: counts, kalibrerad: nej",
        "giltiga: 20 av 20 positioner",
        "max: 200 vid pixel 12",
        "bilder: 1, mättade pixlar: 0",
        "toppar: pixel 12.0 (200), pixel 5.0 (80)",
        "Relativa tal från kameran.",
    ]


def test_farg_and_kant_match_the_prompt(tmp_path, capsys):
    """farg MAPP ger samma rader som color.report, kant MAPP samma som bandgap MAPP."""
    folder = led(tmp_path, "vit", 560, fwhm=200)
    saved = mapp.read(folder)
    assert run(capsys, ["farg", folder]) == (0, color.report(saved["x"], saved["values"], saved["mask"]))
    prov = tmp_path / "prov"
    prov.mkdir()
    rows = ["x_nm,value,valid"] + [f"{x:g},{t:.10g},true" for x, t in zip(X, edge_at(550))]
    (prov / "spectrum.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (prov / "settings.json").write_text(json.dumps({"mode": "transmission"}), encoding="utf-8")
    assert run(capsys, ["kant", prov.as_posix()]) == (0, EXPECTED_550)
    assert run(capsys, ["kant", folder]) == (1, [
        f"Fel: input.missing_data: {folder}: inte en transmissionsmätning (mode transmission)"
    ])


def test_exit_codes(tmp_path, capsys):
    """ANA-01: okänt kommando ger listan och slutkod 2, ett fel ger Fel: och 1."""
    code, rows = run(capsys, [])
    assert code == 2 and rows[0] == "Användning: python -m spectrometer.analys KOMMANDO MAPP [val]"
    assert len(rows) == 1 + len(analys.KOMMANDON)
    code, rows = run(capsys, ["foo"])
    assert code == 2 and rows[0] == "Fel: input.invalid_argument: okänt kommando foo"
    assert run(capsys, ["toppar"]) == (1, ["Fel: input.invalid_argument: MAPP saknas"])
    assert run(capsys, ["toppar", saved_lines(tmp_path), "--max", "2"])[1] == ["Fel: input.invalid_argument: okänt val --max"]


def test_as_a_program():
    """python -m spectrometer.analys utan kommando: listan och slutkod 2."""
    done = subprocess.run([sys.executable, "-m", "spectrometer.analys"], cwd=ROT, capture_output=True, timeout=60)
    assert done.returncode == 2
    assert "toppar MAPP" in done.stdout.decode("utf-8")


def test_analysis_lists_its_modules():
    """analysis.MODULER: varje modul som listas går att importera."""
    for name in analysis.MODULER:
        importlib.import_module(f"spectrometer.analysis.{name}")
