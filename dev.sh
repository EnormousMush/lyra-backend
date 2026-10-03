#!/usr/bin/env bash
# Start Lyra Studio locally: API on :8765, web app on :5173 (Vite picks the next free
# port if 5173 is taken). Ctrl+C stops both. Override the API port with LYRA_API_PORT.
set -e
cd "$(dirname "$0")"
export LYRA_API_PORT="${LYRA_API_PORT:-8765}"

if lsof -nP -iTCP:"$LYRA_API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $LYRA_API_PORT is already in use by another program:"
  lsof -nP -iTCP:"$LYRA_API_PORT" -sTCP:LISTEN
  echo "Run again with a free port, for example:  LYRA_API_PORT=8877 ./dev.sh"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -x web/node_modules/.bin/vite ]; then
  (cd web && npm install)
fi

[ -f .env ] || echo "No .env found: running in preview mode. Copy .env.example to .env and add your keys."

uvicorn app.main:app --reload --port "$LYRA_API_PORT" &
API=$!
trap 'kill $API 2>/dev/null' EXIT
(cd web && npm run dev)
