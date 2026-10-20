cat > spektro <<'EOF'
#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ ! -x "$UV" ]; then
  echo "Installerar uv, en gång per dator..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "Första gången: hämtar Python 3.12 och bygger miljön..."
  "$UV" venv --seed --python 3.12 "$ROOT/.venv"
fi
"$UV" pip install -q --python "$PY" -r "$ROOT/requirements.txt"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" exec "$PY" -m spectrometer.main "$@"
EOF
chmod +x spektro
echo quit | ./spektro
"$(command -v uv || echo ~/.local/bin/uv)" --version
git status --short