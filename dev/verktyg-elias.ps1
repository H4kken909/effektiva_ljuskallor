# verktyg-elias.ps1: kontroller och protokoll för Elias. Windows PowerShell 5.1 och PowerShell 7.
# Ladda i repots rot med:  . .\verktyg-elias.ps1
# Kommandon:
#   kolla [-k "<uttryck>"]                       kör ruff check . och pytest, skriver OK eller FEL
#   anteckna -Del "<del>" -Vad "<vad>" [-Resultat "OK"] [-Not "<text>"]
#                                                lägger en rad i PROTOKOLL-ELIAS.md
#   klar -Del "<del>" -Vad "<vad>" [-k "<uttryck>"] [-Not "<text>"]
#                                                kolla + anteckna + git add PROTOKOLL-ELIAS.md
#   kor [-W] <fil>                               matar en kommandofil till python -m spectrometer.main
# Filen är UTF-8 med BOM med flit: Windows PowerShell 5.1 läser en .ps1 utan BOM som ANSI, och här står å, ä och ö.

# UTF-8 mellan PowerShell och Python (samma tre rader som i Adrians verktyg.ps1).
$env:PYTHONUTF8 = "1"
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8

# Mappen där den här filen ligger: repots rot. Protokollet och git-raderna utgår från den.
$global:EliasRot = $PSScriptRoot
if (-not $global:EliasRot) { $global:EliasRot = (Get-Location).Path }

# Invoke-EliasSteg: kör ett program, ger Ok (utgångskod 0) och alla utskriftsrader. Inget fel stoppar skriptet.
function Invoke-EliasSteg {
  param([string]$Program, [string[]]$Argument)
  $ErrorActionPreference = "Continue"
  $rader = @()
  $kod = 1
  if (-not (Get-Command $Program -ErrorAction SilentlyContinue)) {
    $rader = @($Program + " hittades inte. Är .venv aktiverad?")
  } else {
    $rader = @(& $Program @Argument 2>&1 | ForEach-Object { "$_" })
    $kod = $LASTEXITCODE
  }
  return [pscustomobject]@{ Ok = ($kod -eq 0); Rader = $rader }
}

# Invoke-EliasKolla: kör ruff och pytest, skriver OK/FEL och sista raderna, ger Ok och Fel (vilka steg som föll).
function Invoke-EliasKolla {
  param([string]$k)
  $ruff = Invoke-EliasSteg -Program "ruff" -Argument @("check", ".")
  $pa = @("-m", "pytest", "-q", "-p", "no:cacheprovider")
  if ($k) { $pa += @("-k", $k) }
  $pytest = Invoke-EliasSteg -Program "python" -Argument $pa
  $fel = @()
  if ($ruff.Ok) { Write-Host "OK   ruff check ." } else { Write-Host "FEL  ruff check ."; $fel += "ruff" }
  $ruff.Rader | Select-Object -Last 6 | ForEach-Object { Write-Host ("     " + $_) }
  if ($pytest.Ok) { Write-Host "OK   pytest" } else { Write-Host "FEL  pytest"; $fel += "pytest" }
  $pytest.Rader | Select-Object -Last 4 | ForEach-Object { Write-Host ("     " + $_) }
  $alla = ($fel.Count -eq 0)
  if ($alla) { Write-Host "OK" } else { Write-Host "FEL" }
  return [pscustomobject]@{ Ok = $alla; Fel = $fel }
}

# kolla: ruff check . och python -m pytest -q -p no:cacheprovider, med -k om du anger ett uttryck.
function kolla {
  param([string]$k)
  $null = Invoke-EliasKolla -k $k
}

# anteckna: lägger en rad i PROTOKOLL-ELIAS.md i repots rot (skapar filen med rubrik om den saknas).
function anteckna {
  param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Del,
    [Parameter(Mandatory = $true, Position = 1)][string]$Vad,
    [string]$Resultat = "OK",
    [string]$Not = ""
  )
  $ErrorActionPreference = "Continue"
  $rot = $global:EliasRot
  $fil = Join-Path $rot "PROTOKOLL-ELIAS.md"
  $utf8 = New-Object System.Text.UTF8Encoding $false
  $inv = [System.Globalization.CultureInfo]::InvariantCulture
  $nu = Get-Date

  # Commit: kort hash för HEAD, och (+ändringar) om något annat är ändrat. Kollas före raden skrivs.
  $commit = ""
  $kort = @(git -C $rot rev-parse --short HEAD 2>$null)
  if ($LASTEXITCODE -eq 0 -and $kort.Count -gt 0) { $commit = ("" + $kort[0]).Trim() } else { $commit = "ingen" }
  $andrat = @(git -C $rot status --porcelain 2>$null)
  if ($LASTEXITCODE -eq 0 -and $andrat.Count -gt 0) { $commit = $commit + " (+ändringar)" }

  # Dator: operativsystem och datornamn.
  $os = "Windows"
  if (Get-Variable -Name IsLinux -ErrorAction SilentlyContinue) {
    if ($IsLinux) { $os = "Linux" } elseif ($IsMacOS) { $os = "macOS" }
  }
  $dator = $os + " " + [System.Environment]::MachineName

  $celler = @(
    $nu.ToString("yyyy-MM-dd", $inv), $nu.ToString("HH:mm", $inv),
    $Del, $Vad, $Resultat, $commit, $dator, $Not
  )
  $delar = @()
  foreach ($c in $celler) {
    $c = (("" + $c) -replace '[\r\n]+', ' ') -replace '\|', '/'
    $c = $c.Trim()
    if ($c -eq "") { $delar += " " } else { $delar += (" " + $c + " ") }
  }
  $rad = "|" + ($delar -join "|") + "|"

  # Filen: skapas med rubrik om den saknas. Radslutet följer filen, och en saknad sista radbrytning läggs till.
  $nl = "`n"
  $text = ""
  if (Test-Path -LiteralPath $fil) {
    $text = [System.IO.File]::ReadAllText($fil, $utf8)
    if ($text.Contains("`r`n")) { $nl = "`r`n" }
  } else {
    $huvud = @(
      "# Protokoll: Elias",
      "",
      "Här skriver klar och anteckna en rad direkt efter varje delkontroll, före commit.",
      "",
      "| Datum | Tid | Del | Vad | Resultat | Commit | Dator | Not |",
      "|---|---|---|---|---|---|---|---|"
    )
    $text = ($huvud -join $nl) + $nl
    [System.IO.File]::WriteAllText($fil, $text, $utf8)
  }
  $prefix = ""
  if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $prefix = $nl }
  [System.IO.File]::AppendAllText($fil, $prefix + $rad + $nl, $utf8)
  Write-Host ("Protokoll: " + $rad)
}

# klar: kolla, anteckna med resultatet (OK eller FEL (steg)), git add PROTOKOLL-ELIAS.md och git status --short.
function klar {
  param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Del,
    [Parameter(Mandatory = $true, Position = 1)][string]$Vad,
    [string]$k,
    [string]$Not = ""
  )
  $res = Invoke-EliasKolla -k $k
  $resultat = "OK"
  if (-not $res.Ok) { $resultat = "FEL (" + ($res.Fel -join ", ") + ")" }
  anteckna -Del $Del -Vad $Vad -Resultat $resultat -Not $Not
  git -C $global:EliasRot add PROTOKOLL-ELIAS.md
  git -C $global:EliasRot status --short
}

# kor: matar en kommandofil till programmet. -W gör varningar till fel (python -W error).
function kor {
  param(
    [switch]$W,
    [Parameter(Mandatory = $true, Position = 0)][string]$Fil
  )
  if (-not (Test-Path -LiteralPath $Fil)) {
    Write-Host ("FEL: filen finns inte: " + $Fil)
    return
  }
  $flaggor = @()
  if ($W) { $flaggor = @("-W", "error") }
  Get-Content -Encoding UTF8 -LiteralPath $Fil | python @flaggor -m spectrometer.main
}
