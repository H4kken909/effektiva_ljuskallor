# Demo: kommandofiler och reserv

Kommandofilerna är en rad per kommando, utan kommentarer. Förklaringarna står här. De körs från projektets rotmapp.

Provat: att varje rad är ett riktigt kommando, och att `reserv.txt` går igenom hela kedjan på påhittade bilder (`tests/test_demo.py`). Inte provat: filerna mot en riktig kamera.

## Det som saknas tills riggen är klar

Bilderna i `demo/bilder/`, `demo/punkter.csv` och `demo/kand.csv` finns inte än. De tas och görs på riggen under mätveckorna, med samma kameraläge för alla bilder (se Reservbilder). Tills dess kan `reserv.txt` inte köras. Programmet svarar då `Fel: camera.open_failed: Image source does not exist demo/bilder/mork.png`.

`demo/punkter.csv` har rubriken `pixel,wavelength_nm,check`, pixlarna för lysrörets linjer ur `lysror.png` och kvicksilverlinjernas våglängder (404,656, 435,833, 546,074, 576,960 och 579,066 nm). `demo/kand.csv` har rubriken `wavelength_nm,relative_power_per_nm` och lampans kända fördelning (B5 är inte avgjord). Den ska täcka hela det uppmätta intervallet med lite marginal.

## Filerna

| Fil | Rader | Anmärkning |
|---|---|---|
| `1_forbered.txt` | `source camera 0`, `roi full`, `channel gray`, `frames 16`, `show` | Byt `roi full` mot `roi X Y W H` med bandets uppmätta värden när riggen är klar. `roi full` fungerar men ger sämre kontrast. |
| `2_kalibrera.txt` | `calibrate demo/punkter.csv` | Punktfilen görs på riggen. |
| `3_mata.txt` | `step`, `save` | Körs två gånger: först direkt, sedan i transmission. |
| `reserv.txt` | hela kedjan på sparade bilder | Se Reservplan. Slutar med `save`, inte `quit`. |

Mörker och referens skrivs för hand, eftersom en människa ska blockera ljusvägen respektive ta bort provet. Ordningen vid demon:

1. Kör `1_forbered.txt`.
2. Skriv `dark` (ljusvägen blockerad, kartongen bort efteråt).
3. Kör `2_kalibrera.txt`.
4. Kör `3_mata.txt`. Det är direkt mätning.
5. Skriv `reference` (utan prov) och `mode transmission`. Sätt in provet. Kör `3_mata.txt` igen.

Jawad-läget: delarna 1 och 2 är redan körda. Jawad skriver själv de fem kommandona `dark`, `reference`, `mode transmission`, `step` och `save` (snabbkortet, `docs/snabbkort.md`). Prov och kartong håller någon annan.

## Så körs en fil

Vid prompten: `run demo/1_forbered.txt`. Varje rad skrivs ut med `spektro>` före, och uppsättningen finns kvar efteråt, så du skriver vidare själv (`dark`, `step`, `save`). Ordningen mellan `dark` och `calibrate` spelar ingen roll.

`run` stannar vid första raden som ger fel och skriver filen och radnumret sist på felraden, till exempel `Fel: camera.open_failed: Image source does not exist demo/bilder/mork.png (demo/reserv.txt rad 5)`. Rätta och kör filen igen.

Vill du köra en fil direkt när programmet startar: `python -m spectrometer.main --kor demo/1_forbered.txt`. Sedan kommer prompten som vanligt.

Genom en pipe (`Get-Content demo\1_forbered.txt | python -m spectrometer.main`, på Arch `python -m spectrometer.main < demo/1_forbered.txt`) avslutas programmet efter sista raden och uppsättningen försvinner. Ett fel stoppar inte heller filen: programmet fortsätter med nästa rad, så läs efter rader som börjar med `Fel:`.

## Reservplan i tre nivåer

Skriv ut den som ett papper. Beslutsregel: efter tre minuter utan bild, gå till nästa nivå.

1. **Kameran hittas inte.** Prova en annan USB-port eller ett annat nummer (`source camera 1`) och `python check_install.py --kamera N`. Stäng Teams och Kamera-appen.
2. **Kameran ger mörk eller fel bild.** Ställ om exponeringen med `v4l2-ctl` (Arch) eller drivrutinsrutan (Windows) och mät igen. Att köra `step` en gång till hjälper inte: kameran öppnas om vid varje `step`.
3. **Allt annat.** Skriv `run demo/reserv.txt` vid prompten och säg det öppet: det här är sparade bilder från riggen, inte en live-mätning.

## Reservbilder (tas på riggen)

En uppsättning, tagen i samma kameraläge (exponering, gain, upplösning):

| Fil | Bilden |
|---|---|
| `mork.png` | ljusvägen blockerad |
| `lysror.png` | lysrör, för kalibreringen |
| `lampa_kand.png` | den kända lampan, för responsen |
| `referens.png` | ljuskällan utan prov |
| `prov.png` | provet med filter i ljusvägen |

Lägg `demo/bilder/kamera.txt` bredvid med exponering, gain och avståndet mellan kamera och spalt. Spara kopior på USB-minne och i mätdata-repot. Bilderna är 8 bitar och sparade som PNG.

## En fil för hela mätningen: mät.txt

`run demo/mät.txt` kör mätningen i ordning: `dark`, `calibrate demo/punkter.csv`, `response build demo/kand.csv`, `response on`, `step`, `save`, `color`, `figure data/figur.png` (rapportfiguren, skrivs över varje gång) och `guide`. Källan och ROI:n ställs först (`1_forbered.txt`). I en terminal ber `dark` om kartongen, och `pause` väntar på Enter medan lampan byts; skriv `avbryt` för att stoppa filen. Efteråt visar `guide` vad som är gjort och nästa steg, och `help limits` vad talen inte säger.

Provat: hela filen på påhittade bilder med låtsaskamera (`tests/test_demoflode.py`). Inte provat: med riktig kamera och lampbyte. `figure` står i filen sedan 1.2.16.
