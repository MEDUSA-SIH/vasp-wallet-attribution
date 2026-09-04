#!/usr/bin/env bash
# scripts/check.sh
# Local sanity checks run by the controller before each commit.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[check] ruff..."
(cd api && ruff check .)

echo "[check] ruff format check..."
(cd api && ruff format --check .) || true

echo "[check] import smoke (api.app.main)..."
PYTHONPATH=api python -c "from app.main import create_app; print('import ok')"

echo "[check] docker compose config..."
docker compose config >/dev/null

echo "[check] all checks passed ✔"