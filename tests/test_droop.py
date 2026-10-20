"""1.2.6 series plot: relativ uteffekt mot ström (Krav 18) och droop (Krav 21) ur serie.csv, en kurva per serie."""

import matplotlib.pyplot as plt
import numpy as np
import pytest
from test_elias import new_state

from spectrometer import plot, registry
from spectrometer.analysis import series

I0 = 40.0  # syntetisk LED med känd droop: S = I / (1 + I/I0), så area/I = 1 / (1 + I/I0)


def write_series(data, name, currents, scale=1.0):
    """serie.csv för en låtsasdiod i data/name: area = scale · I / (1 + I/I0) vid varje ström."""
    (data / name).mkdir(parents=True, exist_ok=True)
    for current in currents:
        series.append(data / name / "serie.csv", {"current_mA": current, "area": scale * current / (1 + current / I0)})


def state_in(tmp_path):
    """En ny state med output_dir i tmp_path/data."""
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    return state


def test_droop_of_a_known_led(tmp_path, capsys):
    """ANA-58: rätt relativ effektivitet för S = I/(1 + I/I0); två dioder med olika nivå får samma droop-kurva."""
    data = tmp_path / "data"
    write_series(data, "ny", [10, 20, 40, 80])
    write_series(data, "gammal", [10, 20, 40, 80], scale=0.5)
    target = tmp_path / "droop.png"
    registry.run_command(state_in(tmp_path), f"series plot ny gammal --droop {target.as_posix()}")
    lines = capsys.readouterr().out.splitlines()
    assert lines[1:6] == [
        "  10 mA: relativ uteffekt 8, relativ effektivitet 1",
        "  20 mA: relativ uteffekt 13.3333, relativ effektivitet 0.833333",
        "  40 mA: relativ uteffekt 20, relativ effektivitet 0.625",
        "  80 mA: relativ uteffekt 26.6667, relativ effektivitet 0.416667",
        "  droop: 58 % lägre area/I vid 80 mA än vid max (relativt, inte verkningsgrad)",
    ]
    assert lines[7:9] == ["  10 mA: relativ uteffekt 4, relativ effektivitet 1",
                          "  20 mA: relativ uteffekt 6.66667, relativ effektivitet 0.833333"]
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_power_against_current_in_a_window(tmp_path, monkeypatch):
    """Utan UT.png ett fönster med arean mot strömmen; fönstret stängs efteråt."""
    write_series(tmp_path / "data", "ny", [20, 10])
    seen = []
    monkeypatch.setattr(plot, "show", lambda: seen.extend(line.get_ydata() for line in plt.gcf().axes[0].lines))
    before = plt.get_fignums()
    registry.run_command(state_in(tmp_path), "series plot ny")
    np.testing.assert_allclose(seen[0], [8.0, 20 / 1.5])  # sorterat på ström
    assert plt.get_fignums() == before


def test_series_plot_bad_words(tmp_path):
    """Serie som saknas, --droop med spänning, okänd axel och inget namn ger fel."""
    state = state_in(tmp_path)
    for line, text in (("series plot finns_inte", "finns inte"),
                       ("series plot ny --x voltage --droop", "kräver --x current"), ("series plot ny --x tid", "--x tar current eller voltage"), ("series plot --droop", "NAMN saknas")):
        with pytest.raises(ValueError, match=text):
            registry.run_command(state, line)
