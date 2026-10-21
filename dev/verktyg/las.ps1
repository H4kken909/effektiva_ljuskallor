# Öppnar kamerans inställningsruta (DirectShow), så att exponering, vitbalans och gain kan låsas för hand.
# Användning: .\dev\verktyg\las.ps1 N   (N = kamerans nummer, som i source camera N)
# I rutan: bocka ur Auto för exponering och vitbalans, sätt gain till 0, tryck OK. Rutans namn beror på kameran.
# Antaget: inställningen gäller tills kameran kopplas ur. Prova med info före och efter.
param([int]$N = 0)
python -c "import cv2; c = cv2.VideoCapture($N, cv2.CAP_DSHOW); c.read(); c.set(cv2.CAP_PROP_SETTINGS, 1); input('Ställ in i rutan, tryck sedan Enter här: '); c.release()"
