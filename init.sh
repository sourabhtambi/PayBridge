#!/bin/bash
set -euo pipefail

echo "=== Bootstrapping dev environment ==="

# Backend dependencies
cd backend && uv sync && cd ..

# Frontend dependencies
cd frontend && npm ci && cd ..

# Environment
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your API keys"
fi

# Local dev servers (verification mode: local)
mkdir -p .run
(cd backend && exec uv run uvicorn src.main:app --port 8000 > ../.run/backend.log 2>&1) &
echo $! > .run/backend.pid
(cd frontend && exec npm run dev -- --port 3000 > ../.run/frontend.log 2>&1) &
echo $! > .run/frontend.pid

stop_servers() {
  for f in .run/backend.pid .run/frontend.pid; do
    [ -f "$f" ] && pkill -P "$(cat "$f")" 2>/dev/null || true
    [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null || true
  done
}

# Health checks
echo "Waiting for services..."
for url in http://localhost:8000/health http://localhost:3000; do
  for i in 1 2 3 4 5; do
    if curl -sf "$url" > /dev/null; then echo "OK $url"; break; fi
    [ "$i" = 5 ] && { echo "FAILED $url"; stop_servers; exit 1; }
    sleep $((i * 2))
  done
done

echo "=== Environment ready ==="
