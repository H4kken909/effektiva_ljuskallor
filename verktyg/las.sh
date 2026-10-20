#!/usr/bin/env bash
# Låser kamerans exponering, vitbalans och gain, så att mörker, referens och prov tas med samma inställningar.
# Användning: bash verktyg/las.sh N   (N i /dev/videoN). Kräver v4l2-ctl (paketet v4l-utils).
# Reglagens namn skiljer mellan kameror: se dem med  v4l2-ctl -d /dev/videoN --list-ctrls  och ändra raderna här.
set -eu
AUTO_EXPOSURE=auto_exposure=1            # 1 = manuell exponering på de flesta UVC-kameror (antaget, prova)
WHITE_BALANCE=white_balance_automatic=0  # 0 = ingen automatisk vitbalans
GAIN=gain=0                              # 0 = ingen förstärkning

N=${1:?ange kamerans nummer, till exempel: bash verktyg/las.sh 0}
v4l2-ctl --device="/dev/video$N" --set-ctrl="$AUTO_EXPOSURE,$WHITE_BALANCE,$GAIN"
# Läs tillbaka vad kameran faktiskt tog emot (namnen utan =värde):
v4l2-ctl --device="/dev/video$N" --get-ctrl="${AUTO_EXPOSURE%%=*},${WHITE_BALANCE%%=*},${GAIN%%=*}"
