# Examples

Command files have one command per line, as at the prompt. Empty lines are skipped and everything after `#` is a
comment. Run one from the project folder:

```
spektro> run examples/direct.txt
```

| File | What it does |
|---|---|
| `direct.txt` | direct measurement on the test image `rand_x12.png`, then `step` and `save` |
| `calibrate.txt` | dark, calibration and response on the test images |
| `transmission.txt` | reference without a sample, then `mode transmission` |
| `points.csv` | an example points file for `calibrate` |

They all work without a camera. More about calibration is in `calibration/README.md`.
