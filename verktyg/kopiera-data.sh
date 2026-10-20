#!/usr/bin/env bash
# Kopierar mätdata (data/) till ett USB-minne eller gruppens delade mapp efter varje labbpass. Skriver aldrig över.
# Användning: bash verktyg/kopiera-data.sh /run/media/$USER/USB/matdata   (kopian hamnar i .../ÅÅÅÅ-MM-DD)
# rsync -a: undermappar och tider följer med. --ignore-existing: en fil som redan finns rörs inte. *.partial: halva sparningar.
set -eu
MAL=${1:?ange målmappen, till exempel: bash verktyg/kopiera-data.sh /run/media/\$USER/USB/matdata}
KALLA="$(cd "$(dirname "$0")/.." && pwd)/data"
[ -d "$KALLA" ] || { echo "Ingen data-mapp: $KALLA" >&2; exit 1; }
DIT="$MAL/$(date +%F)"
mkdir -p "$DIT"
FORE=$(find "$DIT" -mindepth 1 -maxdepth 1 -type d | wc -l)
rsync -a --ignore-existing --exclude '*.partial' "$KALLA/" "$DIT/"
EFTER=$(find "$DIT" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "kopierat till $DIT: $((EFTER - FORE)) av $EFTER mätmappar där är nya"
