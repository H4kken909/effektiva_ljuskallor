# Kommandon

Skapad av `python tools/gen_kommandon.py` ur kommandoregistret. Ändra texterna i koden, inte här.

| kommando | syntax | vad | fel |
|---|---|---|---|
| help | help [KOMMANDO] | Kommandot help [KOMMANDO]: en rad per kommando i registret, eller raden och syntaxen för ett kommando. | – |
| quit | quit | Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True); frågar först om en osparad mätning. | – |
| show | show | Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns. | – |
| status | status | Kommandot status: mörker, kalibrering, respons, referens och läge på en rad, sedan nästa steg i kedjan. | – |
| version | version | Kommandot version: programmet, Python, biblioteken, git och operativsystemet på en rad. | – |
| source | source file PATH eller source camera N | Kommandot source file PATH eller source camera N: byter källa och glömmer den gamla bilden. | – |
| roi | roi X Y W H eller roi full | Kommandot roi X Y W H eller roi full; en ROI som inte ryms i senaste bilden ger fel och den gamla står kvar. | – |
| channel | channel gray, sum, red, green eller blue | Kommandot channel NAMN: färgkanal ur calc.CHANNELS. | – |
| axis | axis horizontal eller axis vertical | Kommandot axis RIKTNING: riktning ur session.AXES. | – |
| frames | frames N | Kommandot frames N: antalet bilder per mätning, från 1 till registry.MAX_FRAMES (1000). | – |
| info | info | Kommandot info: öppnar källan, läser en bild, skriver vad källan och drivrutinen säger och stänger igen. | – |
| cameras | cameras | Kommandot cameras: provar kameranummer 0 till 4 med source.probe och skriver en rad per nummer. Källan ändras inte. | – |
| snap | snap | Kommandot snap [N]: läser N bilder ur källan och sparar dem som PNG; state ändras inte. | – |
| image | image | Kommandot image [FIL]: läser en bild och sparar en kopia med ROI:n som grön ram, för att se var ROI:n ligger. | – |
| step | step | Kommandot step: mäter, skriver toppen och antalet bilder, varnar vid mättnad och transmission över 1,05. | – |
| save | save [DIR] | Kommandot save [DIR]: sparar senaste mätningen i en ny mätmapp under DIR eller output_dir. | – |
| start | start [SEKUNDER] | Kommandot start [SEKUNDER]: spektrumet live tills Ctrl+C, tills fönstret stängs eller efter SEKUNDER. | – |
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
| clear | clear dark, clear calibration, clear response, clear reference eller clear all | Kommandot clear NAMN: tar bort mörker, kalibrering, respons, referens, eller allt utom inställningarna. | – |
| set | set min_response TAL, set min_reference TAL eller set output_dir MAPP | Kommandot set NYCKEL VÄRDE för min_response och min_reference (ändliga tal över 0) och output_dir. | – |
| rows | rows, rows mean eller rows median | Kommandot rows [mean\|median]: medel (calc.extract_spectrum) eller median (calc.extract_median) över raderna. | – |
| background | background, background N eller background off | Kommandot background [N\|off]: medianen av N rader på var sida om ROI:n dras av efter mörkret. | – |
| response save | response save FIL.npz | Kommandot response save FIL.npz: x, values, roi, channel, axis, coefficients och pixel_range med np.savez. | ValueError med input.missing_data utan respons, input.invalid_argument om FIL redan finns; OSError om den inte går att skriva. |
| response load | response load FIL.npz | Kommandot response load FIL.npz: som response build, men responsen läses ur filen; response on behövs sedan. | – |
| rigg | rigg, rigg PATH eller rigg off | Kommandot rigg [PATH\|off]: läser rigg.json (fälten i docs/rigg.md) till state["rigg"]; save skriver den. DOK-31. | – |
