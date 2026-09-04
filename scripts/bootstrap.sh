#!/usr/bin/env bash
# scripts/bootstrap.sh
# One-shot bootstrapper: copies .env.example if missing, installs
# pre-commit hooks (if available) and brings the stack up.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
  echo "[bootstrap] .env not found – using .env.example as template"
  cp .env.example .env
fi

# Install pre-commit hooks (best effort)
if command -v pre-commit >/dev/null 2>&1; then
  echo "[bootstrap] installing pre-commit hooks"
  pre-commit install || true
else
  echo "[bootstrap] pre-commit not installed (skipping). Install with: pip install pre-commit"
fi

echo "[bootstrap] docker compose pull (best effort)"
docker compose pull --ignore-pull-failures || true

echo "[bootstrap] docker compose up -d --build"
docker compose up -d --build

echo "[bootstrap] waiting for api health..."
API_PORT_VAL="${API_PORT:-8000}"
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:${API_PORT_VAL}/api/v1/health" >/dev/null 2>&1; then
    echo "[bootstrap] api is healthy ✔"
    exit 0
  fi
  sleep 2
done

echo "[bootstrap] api did not become healthy in time" >&2
exit 1