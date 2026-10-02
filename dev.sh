#!/usr/bin/env bash
# Start Lyra Studio locally: API on :8000, web app on :5173. Ctrl+C stops both.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -d web/node_modules ]; then
  (cd web && npm install)
fi

[ -f .env ] || echo "No .env found: running in preview mode. Copy .env.example to .env and add your keys."

uvicorn app.main:app --reload --port 8000 &
API=$!
trap 'kill $API 2>/dev/null' EXIT
(cd web && npm run dev)
