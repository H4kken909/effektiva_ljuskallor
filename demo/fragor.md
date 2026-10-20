# Förväntade frågor och svar

En sida. Där det står ____ fylls svaret i från riktiga mätningar före demon.

| Fråga | Svar |
|---|---|
| Är y-axeln effekt? | Nej. Det är kamerans relativa counts (8 bitar, efter mörkeravdrag och eventuell responskorrigering). Aldrig watt, lumen eller verkningsgrad. Kurvan visar formen på spektrumet, inte hur starkt ljuset är i absoluta tal. |
| Hur säker är våglängdsaxeln? | `calibrate` skriver kontrollfelet i nm och det giltiga intervallet (`kontrollfel vid pixel …`, `giltigt: pixel … till …`). Senaste kontrollfelet: ____ nm. Kalibreringen gäller bara så länge optiken inte flyttats. |
| Varför är en 8-bitars PNG "rådata"? | Webbkameran lämnar inte ut sensorns råvärden. `raw.png` är den avkodade 8-bitarsbilden, och vi kallar den det. Om det räcker för Krav 12 är en öppen fråga till handledaren (B11). |
| Hur lång tid tar en mätning? | `frames` delat med kamerans bildtakt, plus att kameran öppnas. Mätt tid för `frames 16`: ____ s. |
| Varför tas mörker om? | Programmet minns inget mellan starter, och mörkret beror på exponering, gain och temperatur. Ändras något måste `dark` (och `reference`) tas om. |
| Vilken upplösning har den i nm? | Den bestäms av spalt och optik, inte av programmet. Från Adrians test: ____ nm. |
| Kan det mäta infrarött? | Det beror på kamerans filter. Vi har inte mätt det: ____ . |
| Visar testerna att instrumentet mäter rätt? | Nej. De visar att räkningen stämmer. Att uppställningen ger riktiga spektrum visar bara mätningarna på riggen. |
