# verktyg-elias.sh: kontroller och protokoll för Elias, bash på Arch. Samma kommandon som verktyg-elias.ps1.
# Ladda i repots rot med:  . ./verktyg-elias.sh
# Kommandon:
#   kolla [-k "<uttryck>"]                       kör ruff check . och pytest, skriver OK eller FEL
#   anteckna -Del "<del>" -Vad "<vad>" [-Resultat "OK"] [-Not "<text>"]
#                                                lägger en rad i PROTOKOLL-ELIAS.md
#   klar -Del "<del>" -Vad "<vad>" [-k "<uttryck>"] [-Not "<text>"]
#                                                kolla + anteckna + git add PROTOKOLL-ELIAS.md
#   kor [-W] <fil>                               matar en kommandofil till python -m spectrometer.main

export PYTHONUTF8=1

# Mappen där den här filen ligger: repots rot. Protokollet och git-raderna utgår från den.
_el_rot="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# _el_py: python i den aktiva miljön, annars python3.
_el_py() {
  if command -v python >/dev/null 2>&1; then
    printf 'python'
  else
    printf 'python3'
  fi
}

# _el_kolla: kör ruff och pytest, skriver OK/FEL och sista raderna. Sätter _EL_FEL till de steg som föll.
_el_kolla() {
  local k="$1" py ut rc
  local pa=(-m pytest -q -p no:cacheprovider)
  _EL_FEL=""
  py="$(_el_py)"
  if command -v ruff >/dev/null 2>&1; then
    ut="$(ruff check . 2>&1)"
    rc=$?
  else
    ut="ruff hittades inte. Är .venv aktiverad?"
    rc=127
  fi
  if [ "$rc" -eq 0 ]; then
    echo "OK   ruff check ."
  else
    echo "FEL  ruff check ."
    _EL_FEL="ruff"
  fi
  printf '%s\n' "$ut" | tail -n 6 | sed 's/^/     /'
  if [ -n "$k" ]; then
    pa+=(-k "$k")
  fi
  ut="$("$py" "${pa[@]}" 2>&1)"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "OK   pytest"
  else
    echo "FEL  pytest"
    if [ -n "$_EL_FEL" ]; then
      _EL_FEL="$_EL_FEL, pytest"
    else
      _EL_FEL="pytest"
    fi
  fi
  printf '%s\n' "$ut" | tail -n 4 | sed 's/^/     /'
  if [ -z "$_EL_FEL" ]; then
    echo "OK"
    return 0
  fi
  echo "FEL"
  return 1
}

# kolla: ruff check . och python -m pytest -q -p no:cacheprovider, med -k om du anger ett uttryck.
kolla() {
  local k=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -k|-K)
        if [ $# -lt 2 ]; then echo "kolla: -k behöver ett uttryck" >&2; return 2; fi
        k="$2"; shift 2 ;;
      *) echo "kolla: okänd flagga $1" >&2; return 2 ;;
    esac
  done
  _el_kolla "$k"
}

# anteckna: lägger en rad i PROTOKOLL-ELIAS.md i repots rot (skapar filen med rubrik om den saknas).
anteckna() {
  local del="" vad="" resultat="OK" not="" npos=0
  while [ $# -gt 0 ]; do
    case "${1,,}" in
      -del) del="$2"; shift 2 ;;
      -vad) vad="$2"; shift 2 ;;
      -resultat) resultat="$2"; shift 2 ;;
      -not) not="$2"; shift 2 ;;
      *)
        npos=$((npos + 1))
        if [ "$npos" -eq 1 ]; then del="$1"; elif [ "$npos" -eq 2 ]; then vad="$1"; fi
        shift ;;
    esac
  done
  if [ -z "$del" ] || [ -z "$vad" ]; then
    echo 'anteckna: använd  anteckna -Del "<del>" -Vad "<vad>" [-Resultat "OK"] [-Not "<text>"]' >&2
    return 2
  fi
  local fil="$_el_rot/PROTOKOLL-ELIAS.md" commit dator os datum tid eol=$'\n'

  # Commit: kort hash för HEAD, och (+ändringar) om något annat är ändrat. Kollas före raden skrivs.
  commit="$(git -C "$_el_rot" rev-parse --short HEAD 2>/dev/null)"
  if [ -z "$commit" ]; then commit="ingen"; fi
  if [ -n "$(git -C "$_el_rot" status --porcelain 2>/dev/null)" ]; then commit="$commit (+ändringar)"; fi

  # Dator: operativsystem och datornamn.
  os="$(uname -s)"
  if [ -r /etc/os-release ]; then
    os="$(. /etc/os-release; if [ "$ID" = "arch" ]; then printf 'Arch'; else printf '%s' "${NAME:-$os}"; fi)"
  fi
  dator="$os $(uname -n)"
  datum="$(date +%F)"
  tid="$(date +%H:%M)"

  local celler=("$datum" "$tid" "$del" "$vad" "$resultat" "$commit" "$dator" "$not")
  local rad="|" c
  for c in "${celler[@]}"; do
    c="${c//$'\r'/ }"
    c="${c//$'\n'/ }"
    c="${c//|//}"
    c="${c#"${c%%[![:space:]]*}"}"
    c="${c%"${c##*[![:space:]]}"}"
    if [ -z "$c" ]; then rad="$rad |"; else rad="$rad $c |"; fi
  done

  # Filen: skapas med rubrik om den saknas. Radslutet följer filen, och en saknad sista radbrytning läggs till.
  if [ ! -e "$fil" ]; then
    printf '%s\n' \
      '# Protokoll: Elias' \
      '' \
      'Här skriver klar och anteckna en rad direkt efter varje delkontroll, före commit.' \
      '' \
      '| Datum | Tid | Del | Vad | Resultat | Commit | Dator | Not |' \
      '|---|---|---|---|---|---|---|---|' > "$fil"
  else
    if grep -q $'\r' "$fil" 2>/dev/null; then eol=$'\r\n'; fi
    if [ -s "$fil" ] && [ -n "$(tail -c1 "$fil")" ]; then printf '%s' "$eol" >> "$fil"; fi
  fi
  printf '%s%s' "$rad" "$eol" >> "$fil"
  echo "Protokoll: $rad"
}

# klar: kolla, anteckna med resultatet (OK eller FEL (steg)), git add PROTOKOLL-ELIAS.md och git status --short.
klar() {
  local del="" vad="" k="" not="" npos=0 resultat="OK"
  while [ $# -gt 0 ]; do
    case "${1,,}" in
      -del) del="$2"; shift 2 ;;
      -vad) vad="$2"; shift 2 ;;
      -k) k="$2"; shift 2 ;;
      -not) not="$2"; shift 2 ;;
      *)
        npos=$((npos + 1))
        if [ "$npos" -eq 1 ]; then del="$1"; elif [ "$npos" -eq 2 ]; then vad="$1"; fi
        shift ;;
    esac
  done
  if [ -z "$del" ] || [ -z "$vad" ]; then
    echo 'klar: använd  klar -Del "<del>" -Vad "<vad>" [-k "<uttryck>"] [-Not "<text>"]' >&2
    return 2
  fi
  if ! _el_kolla "$k"; then resultat="FEL ($_EL_FEL)"; fi
  anteckna -Del "$del" -Vad "$vad" -Resultat "$resultat" -Not "$not"
  git -C "$_el_rot" add PROTOKOLL-ELIAS.md
  git -C "$_el_rot" status --short
}

# kor: matar en kommandofil till programmet. -W gör varningar till fel (python -W error).
kor() {
  local flaggor=() fil="" a
  for a in "$@"; do
    case "$a" in
      -W) flaggor=(-W error) ;;
      *) fil="$a" ;;
    esac
  done
  if [ -z "$fil" ] || [ ! -f "$fil" ]; then
    echo "FEL: filen finns inte: $fil" >&2
    return 1
  fi
  "$(_el_py)" ${flaggor[@]+"${flaggor[@]}"} -m spectrometer.main < "$fil"
}
