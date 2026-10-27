# Sets up and starts spektro on Arch (needs: sudo pacman -S python tk)
set -e
cd "$(dirname "$(readlink -f "$0")")"
if [ ! -x .venv/bin/python ]; then
  python -m venv .venv
fi
.venv/bin/python -m pip install -q -r requirements.txt
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" exec .venv/bin/python spektro.py "$@"
