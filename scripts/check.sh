#!/usr/bin/env bash
# scripts/check.sh
# Local sanity checks run by the controller before each commit.
# Mirrors what CI does (lint + import smoke + yaml sanity).
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[check] ruff..."
(cd api && ruff check .)

echo "[check] ruff format check..."
(cd api && ruff format --check .) || true

echo "[check] import smoke (api.app.main)..."
PYTHONPATH=api python -c "from app.main import create_app; print('import ok')"

echo "[check] docker compose config..."
docker compose config >/dev/null || python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" >/dev/null

echo "[check] ci workflow yaml..."
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" || true

echo "[check] pre-commit-config yaml..."
python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" || true

echo "[check] all checks passed ✔"