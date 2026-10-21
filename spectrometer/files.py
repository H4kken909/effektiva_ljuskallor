"""Sparar mätningar på disk och läser punktfiler och kända fördelningar. Filen räknar inte.

Används av main.py (save, calibrate och response build).
"""
import csv
import hashlib
import json
import math
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from spectrometer import out


def save_measurement(parent, spectrum, image, settings):
    """Sparar en mätning som en mapp med spectrum.csv, raw.png, settings.json och README.txt.

    Säkert: mappen skrivs först som <stämpel>.partial, filerna kontrolleras och sist byter mappen namn (os.replace),
    så en mapp utan .partial är alltid hel. Vid varje fel tas .partial bort; under 50 MB ledigt sparas inget.
    Parametrar: parent: föräldramappen (str eller Path); spectrum: ordboken från measure med x, values, mask,
    x_label och y_label; image: råbilden, (H, W, 3) uint8; settings: inställningarna (bara tal, text, tuple,
    listor, bool och None).
    Returnerar: mätmappen som Path, till exempel data/20261016-153012 eller data/20261016-153012-2.
    Fel: OSError om något inte går att skriva, med files.write_failed om raw.png inte sparas.
    """
    # Mappnamnet är samma ögonblick som measured_at i settings.json, när den finns. DAT-07.
    moment = datetime.fromisoformat(settings["measured_at"]) if "measured_at" in settings else datetime.now()
    stamp = moment.strftime("%Y%m%d-%H%M%S")
    folder = _unused_path(Path(parent), stamp)
    _check_free_space(parent)
    partial = folder.with_name(folder.name + ".partial")
    partial.mkdir(parents=True)
    try:
        _write_files(partial, spectrum, image, settings)
        _check_files(partial)
        _rename(partial, folder)
    except BaseException:
        # Vid varje fel, även Ctrl+C (KeyboardInterrupt) och full disk: hellre ingen mapp än en halv. ROB-12.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return folder


def _write_files(folder, spectrum, image, settings):
    """Skriver spectrum.csv, raw.png, README.txt och settings.json i mappen folder, som redan finns."""
    transmission = settings.get("mode") == "transmission"  # valfritt (0.9.3): kolumnen absorbance
    with open(folder / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        x_col = "x_px" if spectrum["x_label"] == "pixel" else "x_nm"
        header = [x_col, "value", "valid"]
        if transmission:
            header.append("absorbance")
        extra = _extra_columns(spectrum, x_col)  # 1.2.2: raw_counts och x_px sist, så att kolumn 1-3 står kvar
        writer.writerow(header + list(extra))
        for k, (x, value, ok) in enumerate(zip(spectrum["x"], spectrum["values"], spectrum["mask"])):
            cell = f"{value:.10g}" if ok else ""
            row = [f"{x:.10g}", cell, "true" if ok else "false"]
            if transmission:
                # Absorbans A = -log10(T), tom där T saknas eller är 0 eller mindre. Se rev7, Krav 22.
                row.append(f"{-math.log10(value):.10g}" if ok and value > 0 else "")
            writer.writerow(row + [_cell(column[k]) for column in extra.values()])
    save_png(folder / "raw.png", image)
    _write_readme(folder, settings)
    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def load_points(path):
    """
    Läser en punktfil med kolumnerna pixel, wavelength_nm och check.

    Parametrar: path: sökvägen till CSV-filen (str eller Path); check är 0 för anpassning och 1 för kontroll
    Returnerar: (pixels, wavelengths, is_check): pixlar i hela bilden (K,) float64, våglängder i nm (K,) float64 och is_check (K,) bool, True för en kontrollpunkt.
    Fel: ValueError med input.invalid_argument, filnamnet och radnumret vid fel rubrik, fel antal fält, ett fält som inte är ett tal, ett ogiltigt värde eller check som inte är 0 eller 1; OSError om filen saknas.
    """
    name = Path(path).name
    pixels = []
    wavelengths = []
    is_check = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue  # tom rad, en sist i filen är vanlig
            if line_no == 1:
                if row != ["pixel", "wavelength_nm", "check"]:
                    raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade pixel,wavelength_nm,check")
                continue
            if len(row) != 3:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel antal fält, väntade 3")
            try:
                pixel = float(row[0])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: pixel är inte ett tal") from err
            try:
                wavelength = float(row[1])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: wavelength_nm är inte ett tal") from err
            if not math.isfinite(pixel) or pixel < 0:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: pixel har ett ogiltigt värde")
            if row[2] not in ("0", "1"):
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: check ska vara 0 eller 1")
            pixels.append(pixel)
            wavelengths.append(wavelength)
            is_check.append(row[2] == "1")
    pixels = np.array(pixels, dtype=np.float64)
    wavelengths = np.array(wavelengths, dtype=np.float64)
    is_check = np.array(is_check, dtype=bool)
    return pixels, wavelengths, is_check


def load_known(path):
    """Läser en känd fördelning med kolumnerna wavelength_nm och relative_power_per_nm.

    Parametrar: path: sökvägen till CSV-filen (str eller Path).
    Returnerar: (wavelengths, values): våglängder i stigande nm (K,) float64 och relativ effekt per nm (K,) float64.
    Fel: ValueError med input.invalid_argument, filnamnet och radnumret vid fel rubrik, fel antal fält, ett fält som
    inte är ett tal, ett ogiltigt värde, en våglängd som inte stiger eller färre än två datarader; OSError om filen saknas.
    """
    name = Path(path).name
    wavelengths = []
    values = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue  # tom rad, en sist i filen är vanlig
            if line_no == 1:
                if row != ["wavelength_nm", "relative_power_per_nm"]:
                    raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik {row}")
                continue
            if len(row) != 2:
                raise ValueError(f"input.invalid_argument: {name}: fel antal fält, rad {line_no}")
            try:
                wavelength = float(row[0])
                power = float(row[1])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name}: fältet är inte ett tal, rad {line_no}") from err
            if not (math.isfinite(wavelength) and math.isfinite(power)) or power < 0:
                raise ValueError(f"input.invalid_argument: {name}: ogiltigt värde, rad {line_no}")
            if wavelengths and wavelength <= wavelengths[-1]:
                raise ValueError(f"input.invalid_argument: {name}: våglängden stiger inte, rad {line_no}")
            wavelengths.append(wavelength)
            values.append(power)
    if len(wavelengths) < 2:
        raise ValueError(f"input.invalid_argument: färre än två datarader i {name}")
    return np.array(wavelengths, dtype=np.float64), np.array(values, dtype=np.float64)


def save_png(path, image, roi=None):
    """Skriver bilden som PNG; med roi ritas ROI:n som en grön ram på en kopia (råbilden ändras inte).

    Fel: OSError med files.write_failed om filen inte går att skriva.
    """
    if roi is not None:
        image = image.copy()
        x, y, width, height = roi
        cv2.rectangle(image, (x, y), (x + width - 1, y + height - 1), (0, 255, 0), 1)
    try:
        written, encoded = cv2.imencode(".png", image)  # imencode och tofile, inte imwrite: klarar åäö i Windows
        if written:
            encoded.tofile(path)
    except OSError:
        written = False
    if not written:
        raise OSError(f"files.write_failed: {Path(path).name} kunde inte sparas: {path}")


def save_snaps(parent, images):
    """Sparar råbilderna som PNG i parent: snap-ÅÅÅÅMMDD-HHMMSS.png, eller med -001, -002 ... när de är flera.

    En fil som redan finns skrivs inte över; namnet får då -2, -3 ... sist. Returnerar: sökvägarna som Path.
    Fel: OSError, med files.write_failed om en bild inte går att skriva.
    """
    folder = Path(parent)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    paths = []
    for i, image in enumerate(images, start=1):
        stem = f"snap-{stamp}" if len(images) == 1 else f"snap-{stamp}-{i:03d}"
        path = _unused_path(folder, stem, ".png")
        save_png(path, image)
        paths.append(path)
    return paths


def load_lines(path):
    """Läser en linjefil: rubriken wavelength_nm och en våglängd i nm per rad; rader som börjar med # hoppas över.

    Parametrar: path: sökvägen till CSV-filen (str eller Path), t.ex. kalibrering/hg_linjer.csv.
    Returnerar: våglängderna i stigande nm, (L,) float64.
    Fel: ValueError med input.invalid_argument, filnamnet och radnumret vid fel rubrik, fel antal fält, ett fält som
    inte är ett tal eller färre än två linjer; OSError om filen saknas.
    """
    name = Path(path).name
    wavelengths = []
    header = False
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row or row[0].startswith("#"):
                continue  # tom rad eller kommentar (källan för linjerna)
            if not header:
                if row != ["wavelength_nm"]:
                    raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade wavelength_nm")
                header = True
                continue
            if len(row) != 1:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel antal fält, väntade 1")
            try:
                wavelength = float(row[0])
            except ValueError as err:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: wavelength_nm är inte ett tal") from err
            if not math.isfinite(wavelength):
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: wavelength_nm har ett ogiltigt värde")
            wavelengths.append(wavelength)
    if len(wavelengths) < 2:
        raise ValueError(f"input.invalid_argument: färre än två linjer i {name}")
    return np.sort(np.array(wavelengths, dtype=np.float64))


def save_points(path, rows):
    """Skriver en ny punktfil: rubriken pixel,wavelength_nm,check och raderna som de är. Skriver aldrig över.

    Parametrar: path: den nya filen (str eller Path); rows: raderna som text, t.ex. "412.3,404.656,0".
    Returnerar: None.
    Fel: ValueError med input.invalid_argument om filen redan finns; OSError om den inte går att skriva.
    """
    try:
        f = open(path, "x", encoding="utf-8")  # "x": bara en ny fil, annars FileExistsError
    except FileExistsError as err:
        raise ValueError(f"input.invalid_argument: {Path(path).name} finns redan, toppar skriver inte över") from err
    with f:
        f.write("pixel,wavelength_nm,check\n")
        for row in rows:
            f.write(f"{row}\n")


def points_file_info(path):
    """Vilken punktfil kalibreringen kom ifrån: sökvägen, de 12 första tecknen av sha256 och tiden då den lästes.

    Samma sha256 betyder samma innehåll i filen. Parametrar: path: punktfilen (str eller Path).
    Returnerar: {"path": "kalibrering/punkter.csv", "sha256": "3f2a...", "time": "2026-10-20T14:03:12"}.
    Fel: OSError om filen inte går att läsa.
    """
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    return {"path": Path(path).as_posix(), "sha256": digest, "time": datetime.now().isoformat(timespec="seconds")}


def load_saved_calibration(path):
    """Läser kalibreringen ur en mätmapps settings.json (sparad av save, pixel_range finns från 1.0.26).

    Parametrar: path: sökvägen till settings.json (str eller Path).
    Returnerar: ordbok med coefficients (2 eller 3 värden, float64, a0 först), pixel_range (låg, hög),
    axis och image_size ([bredd, höjd]) som de sparades (None om de saknas) och calibration_points_file.
    Fel: ValueError med input.invalid_argument om filen inte är JSON eller värdena har fel form, med
    input.missing_data om kalibreringen eller pixel_range saknas; OSError om filen saknas.
    """
    name = Path(path).name
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    except json.JSONDecodeError as err:
        raise ValueError(f"input.invalid_argument: {name} är inte giltig JSON (rad {err.lineno})") from err
    if not isinstance(saved, dict) or saved.get("coefficients") is None:
        raise ValueError(f"input.missing_data: {name} har ingen kalibrering (coefficients saknas)")
    if saved.get("pixel_range") is None:
        raise ValueError(f"input.missing_data: {name} saknar pixel_range (sparad före 1.0.26), kalibrera med punktfilen")
    try:
        coefficients = np.array(saved["coefficients"], dtype=np.float64)
        low, high = (float(v) for v in saved["pixel_range"])
    except (TypeError, ValueError) as err:
        raise ValueError(f"input.invalid_argument: {name}: coefficients eller pixel_range har fel form") from err
    if coefficients.shape not in ((2,), (3,)) or not np.all(np.isfinite(coefficients)) or not low < high:
        raise ValueError(f"input.invalid_argument: {name}: coefficients eller pixel_range har fel form")
    return {
        "coefficients": coefficients,
        "pixel_range": (low, high),
        "axis": saved.get("axis"),
        "image_size": saved.get("image_size"),
        "calibration_points_file": saved.get("calibration_points_file"),
    }


def save_response(path, wavelengths, values):
    """Skriver responsen som CSV: wavelength_nm, response och valid, med tom cell där responsen saknas (NaN).

    Parametrar: path: filen (str eller Path); wavelengths: (P,) i nm; values: (P,) relativ respons, NaN där ogiltig.
    Fel: OSError om filen inte går att skriva.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["wavelength_nm", "response", "valid"])
        for x, value in zip(wavelengths, values):
            ok = bool(np.isfinite(value))
            writer.writerow([f"{x:.10g}", f"{value:.10g}" if ok else "", "true" if ok else "false"])


SAVED_FILES = ("spectrum.csv", "raw.png", "settings.json", "README.txt")  # filerna som varje hel mätmapp har
MIN_FREE_MB = 50  # en 1080p-PNG är några MB (antaget); under 50 MB ledigt sparas inget


def _unused_path(folder, stem, suffix=""):
    """folder/stem+suffix, eller med -2, -3 ... efter stem när namnet redan finns (en befintlig fil skrivs aldrig över)."""
    path = folder / (stem + suffix)
    counter = 2
    while path.exists():
        path = folder / f"{stem}-{counter}{suffix}"
        counter += 1
    return path


def _check_free_space(parent):
    """Kräver MIN_FREE_MB ledigt på närmaste befintliga mapp ovanför parent. Fel: OSError med files.write_failed."""
    folder = Path(parent).resolve()
    while not folder.exists() and folder != folder.parent:
        folder = folder.parent
    free_mb = shutil.disk_usage(folder).free // (1024 * 1024)
    if free_mb < MIN_FREE_MB:
        raise OSError(f"files.write_failed: bara {free_mb} MB ledigt på {folder.as_posix()}")


def _check_files(folder):
    """Kontrollerar att varje fil i SAVED_FILES finns och inte är tom. Fel: OSError med files.write_failed."""
    for name in SAVED_FILES:
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            raise OSError(f"files.write_failed: {name} saknas eller är tom i {folder.as_posix()}")


def _rename(partial, folder):
    """Byter namn från .partial till det slutliga namnet med os.replace; tre försök vid PermissionError.

    Windows Defender eller OneDrive kan låsa en ny fil en kort stund (antaget), därför en halv sekund mellan försöken.
    """
    for attempt in range(3):
        try:
            os.replace(partial, folder)
            return
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.5)


def opencv_version():
    """OpenCV-versionen, till settings.json och kommandot version (cv2 används bara här och i source.py)."""
    return cv2.__version__


README_TEXT = """\
Mätmapp från spektrometerprogrammet (Effektiva ljuskällor, TFYY51, grupp GRYb1).

Filerna
  spectrum.csv   spektrumet, en rad per position längs spektrumet
  raw.png        den sista råbilden, 8 bitar per kanal
  settings.json  inställningar, programversion, bibliotek, profiler och kalibrering när mätningen gjordes
  README.txt     den här filen

Kolumnerna i spectrum.csv
  x_px eller x_nm  position: pixel i hela bilden (x_px) eller våglängd i nm (x_nm, efter calibrate)
  value            signalen: counts (mode direct), relativ (med respons) eller kvoten T (mode transmission);
                   tom där värdet inte går att använda
  valid            true där värdet går att använda, annars false
  absorbance       bara i mode transmission: A = -log10(T), utan enhet
  raw_counts       signalen i counts efter mörkeravdrag, före respons och transmission (för att räkna om)
  stddev           spridningen mellan bilderna i counts (stickprov), tom vid en bild; inte total osäkerhet
  x_px             bara efter calibrate: pixeln i hela bilden för raden

Alla tal är relativa tal från kameran, inte watt.

Excel: Data, Från text/CSV, välj spectrum.csv, avgränsare komma. Talen har decimalpunkt; visar svensk Excel dem
som text, ändra kolumnernas typ med nationella inställningar Engelska (USA) under Transformera data.
"""


def _write_readme(folder, settings):
    """Skriver README.txt: den fasta texten och raderna om just den här mätningen ur settings. DAT-24."""
    transmission = settings.get("mode") == "transmission"
    lines = [
        "",
        "Den här mätningen",
        f"  källa: {settings.get('source')}",
        f"  kanal: {settings.get('channel')}",
        f"  roi: {settings.get('roi')}",
        f"  frames: {settings.get('frames')}",
        f"  läge: {settings.get('mode')}",
        f"  kalibrerad: {out.YES[settings.get('coefficients') is not None]}",
        f"  mörker: {out.YES[bool(settings.get('dark'))]}",
        f"  respons: {out.YES[bool(settings.get('use_response')) and not transmission]}",
        f"  referens: {out.YES[transmission]}",
        f"  programversion: {settings.get('program_version')}",
        f"  mätt: {settings.get('measured_at')}",
    ]
    (folder / "README.txt").write_text(README_TEXT + "\n".join(lines) + "\n", encoding="utf-8")


def save_roi_image(parent, image, roi):
    """Sparar en kopia av bilden med ROI-rutan (grön) och mättade pixlar (255 i någon kanal) i magenta.

    Parametrar: parent: mappen (str eller Path), skapas om den saknas; image: (H, W, 3) uint8 i BGR; roi: (x, y, w, h).
    Returnerar: sökvägen parent/roi-ÅÅÅÅMMDD-HHMMSS.png (med -2, -3 ... om namnet redan finns).
    Fel: OSError med files.write_failed om bilden inte går att skriva.
    """
    copy = image.copy()
    copy[(image >= 255).any(axis=2)] = (255, 0, 255)
    x, y, w, h = roi
    cv2.rectangle(copy, (x, y), (x + w - 1, y + h - 1), (0, 255, 0), 1)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = _unused_path(Path(parent), f"roi-{stamp}", ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, data = cv2.imencode(".png", copy)
    if not ok:
        raise OSError(f"files.write_failed: {path.name} kunde inte kodas som PNG")
    data.tofile(str(path))  # tofile klarar åäö i sökvägen på Windows, det gör inte cv2.imwrite
    return path


def _extra_columns(spectrum, x_col):
    """Kolumnerna sist i spectrum.csv (1.2.2): raw_counts, stddev (1.2.14) och x_px efter calibrate."""
    extra = {}
    if "raw" in spectrum:
        extra["raw_counts"] = spectrum["raw"]
        if "stddev" in spectrum:  # 1.2.14: spridningen mellan bilderna i counts, tom vid en bild (DAT-02, LOG-14)
            extra["stddev"] = np.where(np.isfinite(spectrum["raw"]), spectrum["stddev"], np.nan)
    if "px" in spectrum and x_col == "x_nm":
        extra["x_px"] = spectrum["px"]
    return extra


def _cell(value):
    """Ett tal som i resten av CSV:n (.10g); tom cell för NaN."""
    return f"{value:.10g}" if np.isfinite(value) else ""


def save_excel(folder):
    """Skriver folder/spectrum_sv.csv ur spectrum.csv för svensk Excel: semikolon, decimalkomma och utf-8 med BOM. 1.2.2.

    Tomma celler står kvar tomma (inte 0); spectrum.csv ändras inte. Returnerar sökvägen.
    Fel: OSError om en fil inte går att läsa eller skriva.
    """
    path = Path(folder) / "spectrum_sv.csv"
    with open(Path(folder) / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        for row in rows:
            writer.writerow([cell.replace(".", ",") for cell in row])
    return path


Y_LABELS = {"transmission": "transmission (kvot)", "response": "korrigerad signal (relativ)", "direct": "signal (counts)"}


def load_measurement(folder):
    """Läser en mätmapp tillbaka: spectrum.csv efter rubrik (inte plats) och settings.json (om den finns). 1.2.2.

    Returnerar: ordboken som measure ger (x, values, mask, x_label, y_label), raw och px när kolumnerna finns, settings
    (ur settings.json, tom ordbok utan filen) och folder. Klarar gamla mappar med tre kolumner.
    Fel: ValueError med input.invalid_argument om rubriken saknar x_nm eller x_px, value eller valid; OSError om filen saknas.
    """
    folder = Path(folder)
    with open(measurement_folder(folder), newline="", encoding="utf-8-sig") as f:  # 1.2.13: Fel-rad, inte [Errno 2]
        reader = csv.reader(f)
        numbered = [(reader.line_num, row) for row in reader if row]
    if not numbered:
        raise ValueError(f"input.invalid_argument: {folder.as_posix()}/spectrum.csv är tom")
    for line_no, row in numbered[1:]:
        if len(row) != len(numbered[0][1]):  # en rad med fel antal fält ger annars IndexError i column
            raise ValueError(f"input.invalid_argument: {folder.name}/spectrum.csv rad {line_no}: fel antal fält")
    rows = [row for _, row in numbered]
    header, body = rows[0], rows[1:]
    x_col = "x_nm" if "x_nm" in header else "x_px"
    if x_col not in header or "value" not in header or "valid" not in header:
        raise ValueError(f"input.invalid_argument: {folder.name}/spectrum.csv saknar x_nm eller x_px, value eller valid")

    def column(name):
        k = header.index(name)
        return np.array([float(row[k]) if row[k] else np.nan for row in body])

    path = folder / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    mode = settings.get("mode", "direct")
    if mode == "direct" and settings.get("use_response"):
        mode = "response"
    valid = header.index("valid")
    spectrum = {
        "x": column(x_col),
        "values": column("value"),
        "mask": np.array([row[valid] == "true" for row in body], dtype=bool),
        "x_label": "pixel" if x_col == "x_px" else "våglängd (nm)",
        "y_label": Y_LABELS.get(mode, "signal (counts)"),
        "settings": settings,
        "folder": folder.as_posix(),
    }
    for key, name in (("raw", "raw_counts"), ("stddev", "stddev"), ("px", "x_px")):  # 1.2.14: stddev om den finns
        if name in header and name != x_col:
            spectrum[key] = column(name)
    spectrum["frames"] = settings.get("frames")  # 1.2.14: antalet bilder bakom medlet, till slumpfelet i fwhm
    return spectrum


def save_columns(path, columns):
    """Skriver en CSV med en kolumn per (rubrik, värden); NaN blir en tom cell, text skrivs som den är.

    Skriver aldrig över. Fel: OSError om filen redan finns (FileExistsError) eller inte går att skriva.
    """
    with open(path, "x", newline="", encoding="utf-8") as f:  # "x": fel om filen redan finns
        writer = csv.writer(f)
        writer.writerow([name for name, _values in columns])
        for row in zip(*(values for _name, values in columns)):
            writer.writerow([v if isinstance(v, str) else ("" if math.isnan(v) else f"{v:.10g}") for v in row])


def save_json(path, data):
    """Skriver data som JSON med indrag och åäö som de är. Skriver aldrig över; fel: OSError som save_columns."""
    with open(path, "x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def measurement_folder(folder):
    """spectrum.csv i mätmappen folder, som Path, efter en kontroll att mappen finns och har filen. 1.2.13.

    load, compare, figure, mix och bandgap läser genom den, så att en fel mapp ger en Fel-rad i stället för rått
    [Errno 2] ... spectrum.csv.
    Fel: ValueError med input.invalid_argument om folder inte finns eller inte har någon spectrum.csv.
    """
    folder = Path(folder)
    if not folder.exists():
        raise ValueError(f"input.invalid_argument: {folder.as_posix()} finns inte")
    if not (folder / "spectrum.csv").is_file():
        raise ValueError(f"input.invalid_argument: {folder.as_posix()} är ingen mätmapp (spectrum.csv saknas)")
    return folder / "spectrum.csv"
