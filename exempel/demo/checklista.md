# Checklista för demon

Slutleverans fredag 2026-11-27, 15:15, P326 Pascal. Bocka av i ordning.

## Datum

- [ ] Senast fredag 2026-11-13: välj demodator, efter det första riktiga kameraprovet. Är Windows (DirectShow) fortfarande inte provat med riktig kamera väljs Arch-laptopen. Ha en andra dator på samma tagg som reserv, startad och med kameran inkopplad.
- [ ] Två generalrepetitioner med en utomstående som aldrig rört programmet och spelar beställare. Klocka dem mot manuset (60 minuter). Allt som fastnar blir en Issue märkt `demo`. Datum sätter gruppen, mellan 1.1.0 och demofrysen.
- [ ] Tisdag 2026-11-24: demofrys. Taggen som då är senast (till exempel `v1.3.0`) är den som används. Därefter bara rättningar, med en ny `betaN` och Adrians omkörning.

## Dagen före (torsdag 2026-11-26)

- [ ] Ren klon vid taggen i en ny mapp på demodatorn: `git clone --branch TAGG ADRESSEN C:\spektro-demo`, sedan venv och installation enligt README.
- [ ] `python check_install.py` skriver `Installationen stämmer.`
- [ ] `python -m pytest -q` är grön.
- [ ] A01 (README-stegen) gjorda på demodatorn.
- [ ] Batterier, laddare, USB-kabel.
- [ ] Utskrivna: manus (`exempel/demo/manus.md`), snabbkortet (`docs/snabbkort.md`), reservplanen (`exempel/demo/README.md`) och frågorna (`exempel/demo/fragor.md`).
- [ ] Reservbilderna, `exempel/demo/punkter.csv` och `exempel/demo/kand.csv` finns i `exempel/demo/` och på USB-minne.

## En timme före

- [ ] Lampan varm (10 minuter).
- [ ] Exponering och gain satta med `v4l2-ctl` (Arch) eller drivrutinsrutan (Windows) och noterade.
- [ ] Mörk plats för `dark`: kartong över objektivet eller ljusvägen. Skärmens ljus riktat bort från uppställningen.
- [ ] Skärm eller projektor speglad, och synlig för alla.
- [ ] `git status` ren.

## Fem minuter före

- [ ] Miljön aktiv (`.\.venv\Scripts\Activate.ps1` eller `source .venv/bin/activate`).
- [ ] Fönstret testat med Alt+Tab.
- [ ] `python -m spectrometer.main`, sedan `show`.
- [ ] Alla vet sin roll (`exempel/demo/manus.md`). Isak har klockan.
