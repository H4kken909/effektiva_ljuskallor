# How to use it

Start with `python spektro.py` (or double click Spektro.pyw on windows). Type `help` to see the commands and `quit` to exit

## Measuring a lamp

1. `source camera 0` and `roi X Y W H` around the spectrum (or `roi full`)
2. `step` and check that the peak is between about 150 and 240, if it says saturated lower the exposure
3. block the light and type `dark`
4. `calibrate POINTSFILE` with known lines (template in examples/calibration/points_TEMPLATE.csv, use `peaks` to find the pixels)
5. `step` again and `save`

`save` makes a folder in data/ with spectrum.csv, raw.png, settings.json and spectrum.png. `save --excel` also makes spectrum_sv.csv for swedish excel

## Transmission

Do 1-4 first, then `reference` without the sample, `mode transmission`, put the sample in and `step`. 1 means all light gets through

## Live

`start` shows the spectrum live, `stop` or Ctrl+C stops it. `view camera on` / `view spectrum on` shows the camera and the curve

## Problems

- `python check_install.py` checks the install, `--camera 1` tests camera 1
- wrong number or another program (Teams, Camera app) is using it
- the log is spektro.log in %APPDATA%\spektro (windows) or ~/.config/spektro (linux)

## Limits

The numbers are relative counts from the camera, not watts or efficiency. 255 is saturated. The calibration only holds if the optics dont move. The tests check the math, not that the instrument measures right
