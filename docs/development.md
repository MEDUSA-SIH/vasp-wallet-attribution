# SIH26182 – Development guide

## Prerequisites

- Python 3.12
- Docker + Docker Compose
- (optional) `uv` for fast Python dependency installs
  https://github.com/astral-sh/uv

## First-time setup

```bash
cp .env.example .env
docker compose up -d --build
make migrate
curl http://localhost:8000/api/v1/health
```

The `make migrate` target applies Alembic migrations to the Postgres
container.

## Day-to-day commands

| Task                          | Command                                    |
|-------------------------------|--------------------------------------------|
| Bring stack up                | `make up`                                  |
| Tail api logs                 | `make logs`                                |
| Open api shell                | `make shell`                               |
| Run tests                     | `make test`                                |
| Lint                          | `make lint`                                |
| Apply migrations              | `make migrate`                             |
| Seed demo data                | `make seed-demo`                           |
| Tear down stack               | `make down`                                |

## Offline demo path (WP-11 / Phase 21/22)

The whole attribution pipeline can be exercised offline, without any
live blockchain API keys. The `DEMO_MODE=true` flag (default) swaps in a
`DemoBlockchainProvider` backed by the synthetic fixtures under
`data/synthetic/`.

### Start the API in demo mode

```bash
# Quickest: run uvicorn directly
cd api
DEMO_MODE=true uvicorn app.main:app --reload --port 8000

# Or via docker compose (DEMO_MODE=true is set in .env.example)
make up
```

### Seed the demo dataset (idempotent)

```bash
make seed-demo
# or, locally:
cd api && python -m scripts.seed_demo_data
```

The seed prints a structured log line including the case / address / tx
counts. The DB upsert step is best-effort: it runs only when Postgres
is reachable.

### Hit the smoke attribution endpoint

Case 1 — direct VASP deposit:

```bash
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case1_suspect_001","chain":"ethereum"}'
```

Expected response (truncated):

```json
{
  "outcome": "single_candidate",
  "insufficient_evidence": false,
  "candidates": [
    {
      "hops": 1,
      "endpoint_role": "vasp",
      "vasp_id": "vasp_alpha",
      "confidence": 0.5,
      "evidence_tier": "tier_2_demo_vasp"
    }
  ]
}
```

Case 5 — mixer stops attribution:

```bash
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case5_suspect_001","chain":"ethereum"}'
```

Expected response (truncated):

```json
{
  "outcome": "insufficient_evidence",
  "insufficient_evidence": true,
  "candidates": [
    {
      "endpoint_role": "mixer",
      "mixer_id": "mixer_demo_a",
      "evidence_tier": "tier_1_mixer_stop"
    }
  ]
}
```

### All 8 synthetic cases at a glance

| Case | Pattern                         | Expected outcome                |
|------|---------------------------------|----------------------------------|
| 1    | Direct VASP deposit             | `single_candidate`              |
| 2    | One intermediary                | `single_candidate`              |
| 3    | Multiple intermediaries         | `single_candidate`              |
| 4    | Multiple candidate VASPs        | `ranked_multi_candidate`        |
| 5    | Mixer                           | `insufficient_evidence`         |
| 6    | Bridge (cross-chain)            | `single_candidate`              |
| 7    | False candidate (high-degree)   | `false_candidate_filtered`      |
| 8    | Ambiguous / insufficient        | `insufficient_evidence`         |

The integration test `api/tests/integration/test_attribution_smoke.py`
exercises all 8 cases end-to-end via `TestClient`.

## Local development without Docker

```bash
cd api
uv venv
uv pip install -e ".[dev]"
cp ../.env.example .env  # edit if needed
uvicorn app.main:app --reload
```

Make sure you have a Postgres + Redis available (locally or remote) and
that `POSTGRES_HOST` / `REDIS_HOST` in `.env` point at them.

## Linting & type-checking

- `ruff check .` runs the linter.
- `ruff format .` auto-formats.
- `mypy api/app` runs static type checks (currently relaxed to
  `ignore_missing_imports = true`).

## Running a single test

```bash
docker compose exec api pytest tests/unit -k test_health
```

## Adding a new model

1. Create `api/app/db/models/<name>.py` extending `BaseModel` and any of
   the mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`).
2. Re-export it from `api/app/db/models/__init__.py`.
3. Generate an Alembic migration:

   ```bash
   docker compose exec api alembic revision --autogenerate -m "add foo"
   docker compose exec api alembic upgrade head
   ```

## Adding a new provider

1. Create `api/app/providers/<chain>.py` extending `BlockchainProvider`.
2. Set `chain_code`.
3. Register it inside `app/main.py` `lifespan()` (later stage) using the
   `ProviderRegistry`.

## Folder conventions

- **Absolute imports inside `api`** – always `from app.xxx import …`.
- **Phase references** – every public class/function must have a
  docstring referencing the relevant spec phase.
- **No secrets in source** – environment variables only.
- **DEMO_MODE first** – new features must respect the offline demo
  pathway (see `app/providers/demo.py`).