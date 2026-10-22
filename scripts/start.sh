#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import socket
for port in (8018,3018):
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:raise SystemExit(f'Port {port} is already occupied. Stop its owner or use the existing server.')
PY
if [ ! -d frontend/.next ]; then
  echo 'Run npm --prefix frontend run build first.'
  exit 1
fi
mkdir -p data
if [ -f .env ]; then
  uv run --env-file .env uvicorn backend.app:app --host 127.0.0.1 --port 8018 &
else
  uv run uvicorn backend.app:app --host 127.0.0.1 --port 8018 &
fi
api_pid=$!
npm --prefix frontend run start &
ui_pid=$!
cleanup() { kill "$api_pid" "$ui_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
printf 'OpenResearch: http://127.0.0.1:3018\nAPI docs: http://127.0.0.1:8018/docs\n'
wait
