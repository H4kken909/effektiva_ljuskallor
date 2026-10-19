# verktyg.ps1: UTF-8 och sex hjalpare for testerna. Ladda med: . .\testprotokoll\verktyg.ps1
# Bara ASCII i filen med flit: Windows PowerShell 5.1 laser en .ps1 utan BOM som ANSI.
$env:PYTHONUTF8 = "1"
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8
# nr: numrerar raderna (som cat -n). Exempel: kor tests\kommandon\testa_04.txt | nr
function nr { $i = 0; $input | ForEach-Object { $i++; "{0,6}  {1}" -f $i, $_ } }
# kor: kor en kommandofil i programmet. -W gor varningar till fel (python -W error).
function kor($fil, [switch]$W) {
  $flaggor = @()
  if ($W) { $flaggor = @("-W", "error") }
  Get-Content -Encoding UTF8 $fil | python @flaggor -m spectrometer.main
}
# lika: byter det som far skilja mellan tva korningar: mappnamnet med tiden och residualer nara 0.
function lika($rader) {
  $rader | ForEach-Object {
    $_ -replace 'data/(\d{8}|\u00C5{4}MMDD)-(\d{6}|HHMMSS)(-\d+)?', 'data/MAPP' -replace 'residual: -?[0-9.]+e-1\d', 'residual: 0'
  }
}
# jamfor: jamfor en facit med en korning, efter lika. Ingen utskrift = lika. Annars: - facit, + korningen.
function jamfor($facit, $ut) {
  $a = Join-Path $env:TEMP "facit.txt"
  $b = Join-Path $env:TEMP "ut.txt"
  [System.IO.File]::WriteAllText($a, ((lika (Get-Content -Encoding UTF8 $facit)) -join "`n") + "`n")
  [System.IO.File]::WriteAllText($b, ((lika $ut) -join "`n") + "`n")
  git --no-pager diff --no-index --no-color -b $a $b
}
# spara: sparar en korning som den ar, UTF-8 utan BOM. Exempel: spara testprotokoll\utskrift08.txt $ut
function spara($fil, $ut) {
  [System.IO.File]::WriteAllText((Join-Path $PWD $fil), ($ut -join "`n") + "`n")
}
# sparafacit: sparar en korning som ny facit (efter lika), UTF-8 utan BOM.
function sparafacit($facit, $ut) {
  [System.IO.File]::WriteAllText((Join-Path $PWD $facit), ((lika $ut) -join "`n") + "`n")
}
