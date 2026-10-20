# kalibrering

- `hg_linjer.csv`: Hg-lampans fem linjer i nm (luft), ur NIST Atomic Spectra Database. `toppar kalibrering/hg_linjer.csv` parar dem med topparna.
- `punkter_MALL.csv`: mallen för punktfilen. Alla pixlar är 0, så `calibrate` vägrar ("samma pixel står två gånger") tills pixlarna är ifyllda. Kopiera den till `punkter.csv` och skriv in pixlarna ur `toppar`.
- `check` är 0 för en anpassningspunkt och 1 för en kontrollpunkt (används inte i anpassningen, bara som prov).
- Upplösning: 576.960 och 579.066 nm ligger 2.1 nm isär. Ger `toppar` två toppar där är upplösningen bättre än 2.1 nm, annars inte.
- En laser eller LED duger som grov kontrollpunkt (check 1) med databladets våglängd, inte som anpassningspunkt. Skriv databladets tolerans i protokollet; billiga laserpekare kan avvika flera nm (antaget).
