"""1.2.4 compare: flera mätmappar i samma figur, en rad per mapp med topp, FWHM och area; --norm jämför formen."""

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pytest
from test_elias import line_image, new_state

from spectrometer import plot, registry


def two_folders(tmp_path):
    """Två mätmappar: linjen 200 med note stark och linjen 100 med note svag. Ger mapparna i ordning."""
    data = tmp_path / "data"
    state = new_state()
    for value, note in ((200, "stark"), (100, "svag")):
        path = tmp_path / f"{note}.png"
        cv2.imwrite(str(path), line_image(value=value))
        for line in (f"source file {path.as_posix()}", f"note {note}", "step", f"save {data.as_posix()}"):
            registry.run_command(state, line)
    return sorted(p.as_posix() for p in data.iterdir())


def shown_curves(monkeypatch):
    """Byter plot.show mot en som sparar kurvorna (x, y, namn) i fönstret i stället för att visa det."""
    seen = []
    monkeypatch.setattr(plot, "show", lambda: seen.extend(
        (line.get_xdata(), line.get_ydata(), line.get_label()) for line in plt.gcf().axes[0].lines))
    return seen


def test_compare_level_and_shape(tmp_path, monkeypatch, capsys):
    """Utan --norm står nivåerna kvar (200 och 100); med --norm är båda toppar 1. Fönstret stängs efteråt."""
    folders = two_folders(tmp_path)
    seen = shown_curves(monkeypatch)
    before = plt.get_fignums()
    capsys.readouterr()
    registry.run_command(new_state(), "compare " + " ".join(folders))
    assert capsys.readouterr().out.splitlines()[:3] == [
        "stark: topp 12 pixel, höjd 200, FWHM 1 pixel, area 200 counts·pixel",
        "svag: topp 12 pixel, höjd 100, FWHM 1 pixel, area 100 counts·pixel",
        "Relativa tal från kameran; inte watt, lumen eller verkningsgrad.",
    ]
    assert [(np.nanmax(y), name) for _x, y, name in seen] == [(200, "stark"), (100, "svag")]
    seen.clear()
    registry.run_command(new_state(), "compare " + " ".join(folders) + " --norm")
    assert [np.nanmax(y) for _x, y, _name in seen] == [1.0, 1.0]
    assert plt.get_fignums() == before


def test_compare_refuses_mixed_units_and_no_folder(tmp_path):
    """Pixel mot nm går inte att lägga i samma axlar; utan MAPP blir det fel."""
    folders = two_folders(tmp_path)
    csv = f"{folders[1]}/spectrum.csv"
    with open(csv, encoding="utf-8") as f:
        text = f.read()
    with open(csv, "w", encoding="utf-8") as f:
        f.write(text.replace("x_px", "x_nm", 1))
    with pytest.raises(ValueError, match="olika enheter"):
        registry.run_command(new_state(), "compare " + " ".join(folders))
    with pytest.raises(ValueError, match="MAPP saknas"):
        registry.run_command(new_state(), "compare --norm")
