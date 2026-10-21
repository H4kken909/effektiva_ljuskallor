# Kopierar mätdata (data\) till ett USB-minne eller gruppens delade mapp efter varje labbpass. Skriver aldrig över.
# Användning: .\dev\verktyg\kopiera-data.ps1 D:\matdata   (kopian hamnar i D:\matdata\ÅÅÅÅ-MM-DD, mappen skapas)
# robocopy /E: alla undermappar. /XC /XN /XO: en fil som redan finns i målet hoppas över. /XD *.partial: halva sparningar.
param([Parameter(Mandatory = $true)][string]$Mal)
$Kalla = Join-Path $PSScriptRoot "..\..\data"
if (-not (Test-Path $Kalla)) { Write-Error "Ingen data-mapp: $Kalla"; exit 1 }
$Dit = Join-Path $Mal (Get-Date -Format "yyyy-MM-dd")
$Fore = if (Test-Path $Dit) { @(Get-ChildItem $Dit -Directory).Count } else { 0 }
robocopy $Kalla $Dit /E /XC /XN /XO /XD *.partial /NP /NFL /NDL /NJH /NJS | Out-Null
$Kod = $LASTEXITCODE  # robocopy: 0 inget nytt, 1 kopierat, upp till 7 utan fel, 8 och över fel
if ($Kod -ge 8) { Write-Error "robocopy gav felkod $Kod"; exit 1 }
$Efter = @(Get-ChildItem $Dit -Directory).Count
Write-Output "kopierat till ${Dit}: $($Efter - $Fore) av $Efter mätmappar där är nya"
exit 0
