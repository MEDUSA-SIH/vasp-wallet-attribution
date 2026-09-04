#!/usr/bin/env bash
# scripts/bootstrap.sh
# One-shot bootstrapper: copies .env.example if missing and brings the stack up.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
  echo "[bootstrap] .env not found – copying from .env.example"
  cp .env.example .env
fi

echo "[bootstrap] docker compose pull"
docker compose pull --ignore-pull-failures || true

echo "[bootstrap] docker compose up -d --build"
docker compose up -d --build

echo "[bootstrap] waiting for api health..."
for i in {1..30}; do
  if curl -fsS "http://localhost:${API_PORT:-8000}/api/v1/health" >/dev/null 2>&1; then
    echo "[bootstrap] api is healthy ✔"
    exit 0
  fi
  sleep 2
done

echo "[bootstrap] api did not become healthy in time" >&2
exit 1