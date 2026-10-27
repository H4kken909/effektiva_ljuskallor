# Calibration

- `hg_lines.csv`: the five lines of the mercury lamp in nm (air), from NIST. `peaks examples/calibration/hg_lines.csv` pairs them with the peaks in the spectrum.
- `points_TEMPLATE.csv`: template for the points file. All pixels are 0, so `calibrate` refuses until you type in the pixels from `peaks`. Copy it to `points.csv` first.
- `check` is 0 for a point used in the fit and 1 for a check point.
- Resolution: 576.960 and 579.066 nm are 2.1 nm apart. If `peaks` finds two peaks there, the resolution is better than 2.1 nm.
- `lamp_A.csv`: CIE standard illuminant A (incandescent lamp, 2856 K), 300 to 830 nm, 100 at 560 nm. Use it with `response build examples/calibration/lamp_A.csv` only if the lamp really is an incandescent lamp near 2856 K, otherwise the response is modelled and not measured.
