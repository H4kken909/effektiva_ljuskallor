"""Sparar mätningar på disk och läser punktfiler och kända fördelningar. Filen räknar inte."""

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

SAVED_FILES = ("spectrum.csv", "raw.png", "settings.json", "README.txt")  # filerna som varje hel mätmapp har
MIN_FREE_MB = 50  # en 1080p-PNG är några MB (antaget); under 50 MB ledigt sparas inget
Y_LABELS = {
    "transmission": "transmission (kvot)",
    "response": "korrigerad signal (relativ)",
    "direct": "signal (counts)",
}


def save_measurement(parent, spectrum, image, settings):
    """Sparar en mätning som en mapp med spectrum.csv, raw.png, settings.json och README.txt; ger mappen som Path.

    Säkert: mappen skrivs först som <stämpel>.partial, filerna kontrolleras och sist byter mappen namn (os.replace),
    så en mapp utan .partial är alltid hel. Vid varje fel tas .partial bort; under 50 MB ledigt sparas inget.
    Mappen heter t.ex. data/20261016-153012 (eller ...-2). settings: bara tal, text, listor, bool, None.
    """
    # Mappnamnet är samma ögonblick som measured_at i settings.json, när den finns.
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
        # Vid varje fel, även Ctrl+C (KeyboardInterrupt) och full disk: hellre ingen mapp än en halv.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return folder


def _write_files(folder, spectrum, image, settings):
    """Skriver spectrum.csv, raw.png, README.txt och settings.json i mappen folder, som redan finns."""
    transmission = settings.get("mode") == "transmission"  # mode transmission ger kolumnen absorbance
    with open(folder / "spectrum.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        x_col = "x_px" if spectrum["x_label"] == "pixel" else "x_nm"
        extra = _extra_columns(spectrum, x_col)  # raw_counts och x_px sist, så att kolumn 1-3 står kvar
        writer.writerow([x_col, "value", "valid"] + (["absorbance"] if transmission else []) + list(extra))
        for k, (x, value, ok) in enumerate(zip(spectrum["x"], spectrum["values"], spectrum["mask"])):
            row = [f"{x:.10g}", f"{value:.10g}" if ok else "", "true" if ok else "false"]
            if transmission:
                # Absorbans A = -log10(T), tom där T saknas eller är 0 eller mindre.
                row.append(f"{-math.log10(value):.10g}" if ok and value > 0 else "")
            writer.writerow(row + [_cell(column[k]) for column in extra.values()])
    save_png(folder / "raw.png", image)
    _write_readme(folder, settings)
    with open(folder / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def _csv_rows(path):
    """Varje icke-tom rad i CSV-filen som (radnummer från 1, fält); en tom rad sist i filen är vanlig."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if row:
                yield line_no, row


def load_points(path):
    """Läser en punktfil med kolumnerna pixel, wavelength_nm och check (0 för anpassning, 1 för kontroll).

    Ger (pixels, wavelengths, is_check): pixlar i hela bilden, våglängder i nm (float64) och True för kontrollpunkter.
    """
    name = Path(path).name
    pixels = []
    wavelengths = []
    is_check = []
    for line_no, row in _csv_rows(path):
        if line_no == 1:
            if row != ["pixel", "wavelength_nm", "check"]:
                raise ValueError(
                    f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade pixel,wavelength_nm,check"
                )
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
    return np.array(pixels, dtype=np.float64), np.array(wavelengths, dtype=np.float64), np.array(is_check, dtype=bool)


def load_known(path):
    """Läser en känd fördelning med kolumnerna wavelength_nm och relative_power_per_nm.

    Ger (wavelengths, values): våglängder i stigande nm och relativ effekt per nm, float64.
    """
    name = Path(path).name
    wavelengths = []
    values = []
    for line_no, row in _csv_rows(path):
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


def load_lines(path):
    """Läser en linjefil: rubriken wavelength_nm och en våglängd i nm per rad; rader som börjar med # hoppas över.

    Ger våglängderna i stigande nm (float64), t.ex. ur kalibrering/hg_linjer.csv.
    """
    name = Path(path).name
    wavelengths = []
    header_seen = False
    for line_no, row in _csv_rows(path):
        if row[0].startswith("#"):
            continue  # kommentar (källan för linjerna)
        if not header_seen:
            if row != ["wavelength_nm"]:
                raise ValueError(f"input.invalid_argument: {name} rad {line_no}: fel rubrik, väntade wavelength_nm")
            header_seen = True
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


def save_png(path, image, roi=None):
    """Skriver bilden som PNG; med roi ritas ROI:n som en grön ram på en kopia (råbilden ändras inte)."""
    if roi is not None:
        image = image.copy()
        _draw_roi_box(image, roi)
    try:
        written, encoded = cv2.imencode(".png", image)  # imencode och tofile, inte imwrite: klarar åäö i Windows
        if written:
            encoded.tofile(path)
    except OSError:
        written = False
    if not written:
        raise OSError(f"files.write_failed: {Path(path).name} kunde inte sparas: {path}")


def _draw_roi_box(image, roi):
    """Ritar ROI-rutan (x, y, bredd, höjd) som en grön ram direkt på image."""
    x, y, width, height = roi
    cv2.rectangle(image, (x, y), (x + width - 1, y + height - 1), (0, 255, 0), 1)


def save_snaps(parent, images):
    """Sparar råbilderna som PNG i parent: snap-ÅÅÅÅMMDD-HHMMSS.png, eller med -001, -002 ... när de är flera.

    En fil som redan finns skrivs inte över; namnet får då -2, -3 ... sist. Ger sökvägarna som Path.
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


def save_points(path, rows):
    """Skriver en ny punktfil: rubriken pixel,wavelength_nm,check och raderna (text, t.ex. "412.3,404.656,0").

    Skriver aldrig över.
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

    Samma sha256 betyder samma innehåll i filen.
    """
    path = Path(path)
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:12],
        "time": datetime.now().isoformat(timespec="seconds"),
    }


def load_saved_calibration(path):
    """Läser kalibreringen ur en mätmapps settings.json (sparad av save, pixel_range finns från 1.0.26).

    Ger coefficients (2 eller 3 värden, float64, a0 först), pixel_range (låg, hög), axis, image_size ([bredd, höjd])
    och calibration_points_file; de tre sista är None om de saknas.
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
        raise ValueError(
            f"input.missing_data: {name} saknar pixel_range (sparad före 1.0.26), kalibrera med punktfilen"
        )
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
    """Skriver responsen som CSV: wavelength_nm, response (relativ) och valid; tom cell där responsen saknas (NaN)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["wavelength_nm", "response", "valid"])
        for x, value in zip(wavelengths, values):
            writer.writerow([f"{x:.10g}", _cell(value), "true" if np.isfinite(value) else "false"])


def _unused_path(folder, stem, suffix=""):
    """folder/stem+suffix, eller med -2, -3 ... efter stem när namnet finns (en befintlig fil skrivs aldrig över)."""
    path = folder / (stem + suffix)
    counter = 2
    while path.exists():
        path = folder / f"{stem}-{counter}{suffix}"
        counter += 1
    return path


def _check_free_space(parent):
    """Kräver MIN_FREE_MB ledigt på närmaste befintliga mapp ovanför parent."""
    folder = Path(parent).resolve()
    while not folder.exists() and folder != folder.parent:
        folder = folder.parent
    free_mb = shutil.disk_usage(folder).free // (1024 * 1024)
    if free_mb < MIN_FREE_MB:
        raise OSError(f"files.write_failed: bara {free_mb} MB ledigt på {folder.as_posix()}")


def _check_files(folder):
    """Kontrollerar att varje fil i SAVED_FILES finns och inte är tom."""
    for name in SAVED_FILES:
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            raise OSError(f"files.write_failed: {name} saknas eller är tom i {folder.as_posix()}")


def _rename(partial, folder):
    """Byter namn från .partial till det slutliga namnet med os.replace; tre försök vid PermissionError.

    Windows Defender eller OneDrive kan låsa en ny fil en kort stund (antaget), därför en halv sekund mellan försöken.
    """
    for _ in range(2):
        try:
            os.replace(partial, folder)
            return
        except PermissionError:
            time.sleep(0.5)
    os.replace(partial, folder)  # tredje försöket: ett fel här går vidare


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
    """Skriver README.txt: den fasta texten och raderna om just den här mätningen ur settings."""
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

    Ger sökvägen parent/roi-ÅÅÅÅMMDD-HHMMSS.png (med -2, -3 ... om namnet redan finns); parent skapas om den saknas.
    """
    copy = image.copy()
    copy[(image >= 255).any(axis=2)] = (255, 0, 255)
    _draw_roi_box(copy, roi)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = _unused_path(Path(parent), f"roi-{stamp}", ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, data = cv2.imencode(".png", copy)
    if not ok:
        raise OSError(f"files.write_failed: {path.name} kunde inte kodas som PNG")
    data.tofile(path)  # tofile klarar åäö i sökvägen på Windows, det gör inte cv2.imwrite
    return path


def _extra_columns(spectrum, x_col):
    """Kolumnerna sist i spectrum.csv: raw_counts, stddev och x_px efter calibrate."""
    extra = {}
    if "raw" in spectrum:
        extra["raw_counts"] = spectrum["raw"]
        if "stddev" in spectrum:  # spridningen mellan bilderna i counts, tom vid en bild
            extra["stddev"] = np.where(np.isfinite(spectrum["raw"]), spectrum["stddev"], np.nan)
    if "px" in spectrum and x_col == "x_nm":
        extra["x_px"] = spectrum["px"]
    return extra


def _cell(value):
    """Ett tal som i resten av CSV:n (.10g); tom cell för NaN."""
    return f"{value:.10g}" if np.isfinite(value) else ""


def save_excel(folder):
    """Skriver folder/spectrum_sv.csv ur spectrum.csv för svensk Excel: semikolon, decimalkomma, utf-8 med BOM.

    Tomma celler står kvar tomma (inte 0); spectrum.csv ändras inte. Ger sökvägen.
    """
    path = Path(folder) / "spectrum_sv.csv"
    with open(Path(folder) / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        for row in rows:
            writer.writerow([cell.replace(".", ",") for cell in row])
    return path


def _read_spectrum_table(folder):
    """spectrum.csv i mätmappen som (rubrikraden, dataraderna), efter kontroll att alla rader har lika många fält."""
    with open(measurement_folder(folder), newline="", encoding="utf-8-sig") as f:  # ger en Fel-rad, inte [Errno 2]
        reader = csv.reader(f)
        numbered = [(reader.line_num, row) for row in reader if row]
    if not numbered:
        raise ValueError(f"input.invalid_argument: {folder.as_posix()}/spectrum.csv är tom")
    header = numbered[0][1]
    for line_no, row in numbered[1:]:
        if len(row) != len(header):  # en rad med fel antal fält ger annars IndexError i column
            raise ValueError(f"input.invalid_argument: {folder.name}/spectrum.csv rad {line_no}: fel antal fält")
    return header, [row for _, row in numbered[1:]]


def load_measurement(folder):
    """Läser en mätmapp tillbaka: spectrum.csv efter rubrik (inte plats) och settings.json (om den finns).

    Ger ordboken som measure ger (x, values, mask, x_label, y_label) med raw, stddev och px när kolumnerna finns, samt
    settings (tom ordbok utan filen), folder och frames. Klarar gamla mappar med tre kolumner.
    """
    folder = Path(folder)
    header, body = _read_spectrum_table(folder)
    x_col = "x_nm" if "x_nm" in header else "x_px"
    if x_col not in header or "value" not in header or "valid" not in header:
        raise ValueError(
            f"input.invalid_argument: {folder.name}/spectrum.csv saknar x_nm eller x_px, value eller valid"
        )

    def column(name):
        k = header.index(name)
        return np.array([float(row[k]) if row[k] else np.nan for row in body])

    settings_path = folder / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
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
    for key, name in (("raw", "raw_counts"), ("stddev", "stddev"), ("px", "x_px")):
        if name in header and name != x_col:
            spectrum[key] = column(name)
    spectrum["frames"] = settings.get("frames")  # antalet bilder bakom medlet, till slumpfelet i fwhm
    return spectrum


def save_columns(path, columns):
    """Skriver en CSV med en kolumn per (rubrik, värden); NaN blir en tom cell, text som den är. Skriver aldrig över."""
    with open(path, "x", newline="", encoding="utf-8") as f:  # "x": fel om filen redan finns
        writer = csv.writer(f)
        writer.writerow([name for name, _values in columns])
        for row in zip(*(values for _name, values in columns)):
            writer.writerow([v if isinstance(v, str) else ("" if math.isnan(v) else f"{v:.10g}") for v in row])


def save_json(path, data):
    """Skriver data som JSON med indrag och åäö som de är. Skriver aldrig över."""
    with open(path, "x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def measurement_folder(folder):
    """spectrum.csv i mätmappen folder, som Path, efter en kontroll att mappen finns och har filen.

    load, compare, figure, mix och bandgap läser genom den, så en fel mapp ger en Fel-rad i stället för rått [Errno 2].
    """
    folder = Path(folder)
    if not folder.exists():
        raise ValueError(f"input.invalid_argument: {folder.as_posix()} finns inte")
    if not (folder / "spectrum.csv").is_file():
        raise ValueError(f"input.invalid_argument: {folder.as_posix()} är ingen mätmapp (spectrum.csv saknas)")
    return folder / "spectrum.csv"
