# Kommandon

Skapad av `python tools/gen_kommandon.py` ur kommandoregistret. Ändra texterna i koden, inte här.

| kommando | syntax | vad | fel |
|---|---|---|---|
| help | help [GRUPP\|snabbstart\|alla\|KOMMANDO], eller help.GRUPP | Kommandot help [GRUPP\|snabbstart\|alla\|KOMMANDO]: grupperna, en grupp, snabbstarten, alla kommandon eller ett. | – |
| quit | quit | Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True); frågar först om en osparad mätning. | – |
| show | show | Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns. | – |
| status | status | Kommandot status: mörker, kalibrering, respons, referens och läge på en rad, sedan nästa steg i kedjan. | – |
| version | version | Kommandot version: programmet, Python, biblioteken, git och operativsystemet på en rad. | – |
| source | source file PATH eller source camera N | Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden. | – |
| roi | roi X Y W H eller roi full | Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden, eller inte lämnar plats åt background N, ger fel och den gamla står kvar. | – |
| channel | channel gray, sum, red, green eller blue | Kommandot channel NAMN: färgkanal ur calc.CHANNELS. | – |
| axis | axis horizontal eller axis vertical | Kommandot axis RIKTNING: riktning ur session.AXES. | – |
| frames | frames N | Kommandot frames N: antalet bilder per mätning, från 1 till registry.MAX_FRAMES (1000). | – |
| info | info | Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen. | – |
| cameras | cameras | Kommandot cameras: provar kameranummer 0 till 4 med source.probe och skriver en rad per nummer. Källan ändras inte. | – |
| snap | snap | Kommandot snap [N]: läser N bilder ur källan och sparar dem som PNG; state ändras inte. | – |
| image | image | Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger. | – |
| step | step | Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1,05. | – |
| save | save [DIR] [--excel] | Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir. | – |
| start | start [SEKUNDER] | Kommandot start [SEKUNDER]: spektrumet live tills Ctrl+C eller q, tills fönstret stängs eller efter SEKUNDER. | – |
| stability | stability | Kommandot stability [N]: N bilder i rad med samma källa; skriver hur toppvärdet varierar och driver. | – |
| perf | perf | Kommandot perf [N]: N mätningar med nuvarande källa, ROI, kanal och frames, utan fönster; skriver tiderna. | – |
| calibrate | calibrate PATH [DEGREE [MARGIN]] | Kommandot calibrate PATH [DEGREE [MARGIN]]: anpassar våglängden till punktfilen och prövar mot kontrollpunkterna. | ValueError med input.invalid_argument vid fel ord, fel i punktfilen, för få punkter eller en linje som inte är monoton i det giltiga intervallet; OSError om filen saknas. Den gamla kalibreringen står då kvar. |
| toppar | toppar | Kommandot toppar [N]: de N högsta topparna (efter calibrate även nm); toppar LINJEFIL [UT.csv]: punktfilsförslag. | ValueError med input.missing_data utan mätning, input.invalid_argument vid fel ord. |
| dark | dark [N] | Kommandot dark [N]: mörkret som medel av N bilder (CAPTURE_FRAMES utan N). Det gamla står kvar vid fel. | – |
| response | response build KNOWNFILE [N], response on, response off eller response export PATH | Kommandot response build KNOWNFILE [N], response on, response off eller response export PATH. | – |
| reference | reference [N] eller reference check [N] | Kommandot reference [N]: referensen utan prov, utan respons och transmission, sparad med kanalen. | – |
| mode | mode direct eller mode transmission | Kommandot mode direct eller mode transmission (transmission kräver en referens). | – |
| run | run FIL | Kommandot run FIL: kör raderna i FIL som om de skrevs vid prompten, och skriver spektro> RAD före svaret. | ValueError med input.invalid_argument vid mer än MAX_DEPTH nivåer run; felet från raden med (FIL rad N) sist. |
| wait | wait SEKUNDER | Kommandot wait SEKUNDER: väntar 1 till MAX_WAIT hela sekunder; Ctrl+C avbryter (main skriver Avbrutet.). | ValueError med input.invalid_argument om SEKUNDER inte är ett heltal från 1 till MAX_WAIT. |
| reset | reset eller reset ja | Kommandot reset [ja]: ny state med DEFAULTS. I en terminal frågar det först om något går förlorat; undo ångrar. | ValueError med input.invalid_argument om ordet efter reset inte är ja. |
| undo | undo | Kommandot undo: lägger tillbaka state från före senaste ändrande raden vid prompten; mätningen glöms. | ValueError med input.missing_data när inget finns att ångra (rader i run FIL ångras som en enda rad). |
| history | history [N] | Kommandot history [N]: de N senaste raderna som skrevs vid prompten, numrerade från början av sessionen. | – |
| history save | history save FIL | Kommandot history save FIL: raderna utan fel och inte ångrade, utan NOT_SAVED, i en ny kommandofil. | ValueError med input.invalid_argument om FIL redan finns (skriver aldrig över); OSError om den inte går att skriva. |
| clear | clear dark, clear calibration, clear response, clear reference eller clear all | Kommandot clear NAMN: tar bort mörker, kalibrering, respons eller referens; all tar alla fyra, inget annat. | – |
| set | set min_response TAL, set min_reference TAL eller set output_dir MAPP | Kommandot set NYCKEL VÄRDE för min_response och min_reference (ändliga tal över 0) och output_dir. | – |
| rows | rows, rows mean eller rows median | Kommandot rows [mean\|median]: medel (calc.extract_spectrum) eller median (calc.extract_median) över raderna. | – |
| background | background, background N eller background off | Kommandot background [N\|off]: medianen av N rader på var sida om ROI:n dras av efter mörkret. | – |
| response save | response save FIL.npz | Kommandot response save FIL.npz: x, values, roi, channel, axis, coefficients och pixel_range med np.savez. | ValueError med input.missing_data utan respons, input.invalid_argument om FIL redan finns; OSError om den inte går att skriva. |
| response load | response load FIL.npz | Kommandot response load FIL.npz: som response build, men responsen läses ur filen; response on behövs sedan. | – |
| dark save | dark save FIL.npy | Kommandot dark save FIL.npy: mörkret, (H, W, 3) i counts, med np.save som float32 (halva filen). 1.2.14. | ValueError med input.missing_data utan mörker, input.invalid_argument om FIL redan finns; OSError om den inte går att skriva. |
| dark load | dark load FIL.npy | Kommandot dark load FIL.npy: som dark, men mörkret läses ur filen. 1.2.14. | – |
| rigg | rigg, rigg PATH eller rigg off | Kommandot rigg [PATH\|off]: läser rigg.json (fälten i docs/rigg.md) till state["rigg"]; save skriver den. DOK-31. | – |
| theme | theme light eller theme dark | Kommandot theme light eller theme dark: färgerna i nästa fönster (start, graf); theme ensam visar valet. | – |
| view | view | Kommandot view: vad nästa fönster (start, graf) visar. Ändrar bara visningen, aldrig en mätning. | – |
| graf | graf | Kommandot graf: senaste mätningen med samma rubrik och rutor som live, i ett fönster som väntar tills det stängs. | – |
| roi show | roi show | Kommandot roi show: kopia av senaste bilden med ROI-rutan och mättade pixlar i magenta; sökvägen skrivs. | – |
| roi auto | roi auto | Kommandot roi auto: skriver ett förslag; du godtar det genom att skriva raden. | – |
| roi profile | roi profile | Kommandot roi profile: tre rader om bandet tvärs spektrumet (rader vid horizontal, kolumner vid vertical). | – |
| roi band | roi band | Kommandot roi band START WIDTH: rader START till START+WIDTH vid horizontal, kolumner vid vertical. | – |
| roi move | roi move | Kommandot roi move DX DY: flyttar ROI:n; kontrolleras mot senaste bilden som roi X Y W H. | – |
| axis detect | axis detect | Kommandot axis detect: vågrätt eller lodrätt band ur de ljusa pixlarnas rektangel; skriver ett förslag. | – |
| exposure | exposure N | Kommandot exposure N: exponeringen som sätts varje gång kameran öppnas. Kör auto off först. | – |
| gain | gain N | Kommandot gain N: förstärkningen som sätts varje gång kameran öppnas. | – |
| auto | auto on eller auto off | Kommandot auto on eller auto off: med auto på ändrar kameran exponeringen själv, och då går serier inte att jämföra. | – |
| note | note [TEXT...] eller note clear | Kommandot note TEXT: fri text till settings.json (och serie.csv) vid varje save, tills den byts. Mätningen står kvar. | – |
| series start | series start NAMN | Kommandot series start NAMN: mätmapparna i output_dir/NAMN och en rad per save i serie.csv där; finns den fortsätter den. | – |
| series note | series note current_mA=20 voltage_V=2.9 led=röd | Kommandot series note NYCKEL=VÄRDE...: ström, spänning, LED, prov och lampa till varje save tills de byts. | – |
| series stop | series stop | Kommandot series stop: skriver hur många rader serien fick och glömmer series note. Mätningen står kvar. | – |
| series plot | series plot NAMN... [--x current\|voltage] [--droop] [UT.png\|UT.svg] | Kommandot series plot NAMN...: area mot ström (Krav 18), eller med --droop area/I delad med sitt max (Krav 21). | – |
| load | load MAPP | Kommandot load MAPP: spectrum.csv och settings.json ur mätmappen blir senaste mätningen; skriver toppen som step. | – |
| fwhm | fwhm [N] | Kommandot fwhm [N]: topparna i senaste mätningen med linjebredd vid halva höjden, och arean under kurvan. | – |
| compare | compare MAPP... [--norm] | Kommandot compare MAPP... [--norm]: en rad per mapp och kurvorna i ett fönster (Krav 17a och 17b). Ändrar inte state. | – |
| figure | figure UT.png [MAPP...] [--norm] [--xlim MIN MAX] [--log] [--ev] [--cie] | Kommandot figure UT.png\|UT.svg: senaste mätningen, eller mapparna i samma axlar, som egen figur till rapporten. | – |
| color | color | Kommandot color: x, y, färgtemperatur (CCT och Duv, 1.2.15) och relativ ljusstyrka ur senaste mätningen. | ValueError med input.missing_data utan mätning, kalibrering eller respons, eller utan ljus 380–780 nm. |
| mix | mix MAPP_R MAPP_G MAPP_B --target X Y, --cct K, --sweep eller --fwhm W | Kommandot mix MAPP_R MAPP_G MAPP_B och ett val: vikterna som blandar tre LED-mätningar till en färg (Krav 19). | ValueError med input.invalid_argument vid fel ord, med input.missing_data om en mätning inte duger; OSError om en mapp saknas. |
| bandgap | bandgap [MAPP] [--anpassa] | Kommandot bandgap [MAPP] [--anpassa]: E_g i eV och nm, om kanten ligger i fönstret 366–766 nm, och osäkerheten. | ValueError med input.invalid_argument vid fler ord, med input.missing_data utan transmissionsmätning eller utan kant; som load när MAPP inte är en mätmapp. |
| repeat | repeat N [UT.csv] | Kommandot repeat N [UT.csv]: N mätningar i rad med samma källa och inställningar; senaste mätningen står kvar. | ValueError med input.invalid_argument vid fel ord eller om UT.csv redan finns; felen ur measure. |
| linearity | linearity E1 E2 E3 [E4 ...] | Kommandot linearity E1 E2 E3 [E4 ...]: en mätning per exponering, arean och avvikelsen från en rät linje. | ValueError med input.invalid_argument vid färre än tre olika exponeringar, ett ord som inte är ett tal, eller avbryt; felen ur measure. |
| calibrate save | calibrate save FIL.json | Kommandot calibrate save FIL.json: kalibreringen med residualer, kontrollfel, rms, nm per pixel och upplösning. | ValueError med input.missing_data utan kalibrering eller punktfil, med input.invalid_argument om punktfilen har ändrats eller FIL.json redan finns; OSError om filen inte går att skriva. |
| guide | guide | Kommandot guide: källa, ROI, mörker, kalibrering, respons, mätning och sparad, med x för det som är gjort. | – |
| pause | pause TEXT | Kommandot pause TEXT: skriver TEXT och väntar på Enter i en terminal; avbryt stoppar kommandofilen. | – |
| help limits | help limits | Kommandot help limits: en rad per begränsning i LIMITS (samma rader som i README, Begränsningar). | – |
