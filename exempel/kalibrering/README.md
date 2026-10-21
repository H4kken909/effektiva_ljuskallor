# kalibrering

- `hg_linjer.csv`: Hg-lampans fem linjer i nm (luft), ur NIST Atomic Spectra Database. `toppar exempel/kalibrering/hg_linjer.csv` parar dem med topparna.
- `punkter_MALL.csv`: mallen för punktfilen. Alla pixlar är 0, så `calibrate` vägrar ("samma pixel står två gånger") tills pixlarna är ifyllda. Kopiera den till `punkter.csv` och skriv in pixlarna ur `toppar`.
- `check` är 0 för en anpassningspunkt och 1 för en kontrollpunkt (används inte i anpassningen, bara som prov).
- Upplösning: 576.960 och 579.066 nm ligger 2.1 nm isär. Ger `toppar` två toppar där är upplösningen bättre än 2.1 nm, annars inte.
- En laser eller LED duger som grov kontrollpunkt (check 1) med databladets våglängd, inte som anpassningspunkt. Skriv databladets tolerans i protokollet; billiga laserpekare kan avvika flera nm (antaget).
- `lampa_A.csv`: CIE standardljus A (glödlampa vid 2856 K), 300–830 nm i steg om 1 nm, 100 vid 560 nm. Räknad ur CIE:s definition (CIE 15:2004): S(λ) = 100·(560/λ)^5·(e^(c2/(2848·560)) − 1)/(e^(c2/(2848·λ)) − 1) med c2 = 1,435·10^7 nm·K, sex värdesiffror. Kontroll: 92,912 vid 550 nm och 165,03 vid 650 nm. Duger som känd fördelning (`response build exempel/kalibrering/lampa_A.csv`) bara om lampan verkligen är en glödlampa nära 2856 K (B5); annars är den modellerad, inte mätt.
