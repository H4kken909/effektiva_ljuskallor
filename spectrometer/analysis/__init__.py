"""Analys för Krav 17–22: toppar, färg, serier, bandgap. Importerar bara calc, files och NumPy."""

# Modulerna här, med vad de gör. Prompten använder dem genom kommandona, analysskriptet (python -m spectrometer.analys)
# på sparade mätmappar. Topparna för kalibreringen ligger i spectrometer/peaks.py, mörker, respons och referens i calc.py.
MODULER = {
    "peaks": "toppar, linjebredd (FWHM) och area",
    "color": "CIE 1931 xy, färgtemperatur (McCamy), V(λ), Planck och RGB-blandning",
    "bandgap": "eV, absorbans och absorptionskanten",
    "series": "mätserier: serie.csv, uteffekt mot ström och droop",
    "mapp": "läser en sparad mätmapp (spectrum.csv och settings.json) och kontrollerar hur den sparades",
}
