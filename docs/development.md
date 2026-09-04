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
      "candidate": {"terminal_role": "vasp", "vasp_id": "vasp_alpha", "hops": 1},
      "proximity_rank": 3.0,
      "confidence_score": 77.5,
      "confidence_band": "high",
      "evidence_tier": 1,
      "evidence_tier_label": "Tier 1 — Direct VASP deposit label",
      "explanation": "Terminal wallet is tagged as a deposit of 'vasp_alpha' (VASP Alpha deposit). …"
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
      "candidate": {"terminal_role": "mixer", "mixer_id": "mixer_demo_a"},
      "confidence_score": 0.0,
      "confidence_band": "low",
      "evidence_tier": 99,
      "explanation": "Funds reached a known mixer (mixer_demo_a); attribution stops here per Phase 14 hard rule. …"
    }
  ]
}
```

### All 8 synthetic cases at a glance

| Case | Pattern                         | Outcome                       | Tier | Confidence (band) |
|------|---------------------------------|-------------------------------|------|--------------------|
| 1    | Direct VASP deposit             | `single_candidate`            | 1    | ~78 (high)         |
| 2    | One intermediary                | `single_candidate`            | 2    | ~78 (high)         |
| 3    | Multiple intermediaries         | `single_candidate`            | 3    | ~82 (high)         |
| 4    | Multiple candidate VASPs        | `ranked_multi_candidate`      | 2    | ~78 (high)         |
| 5    | Mixer                           | `insufficient_evidence`       | 99   | 0.0 (low)          |
| 6    | Bridge (cross-chain)            | `single_candidate`            | 3    | ~74 (high)         |
| 7    | False candidate (high-degree)   | `false_candidate_filtered`    | 4    | ~49 (medium)       |
| 8    | Ambiguous / insufficient        | `insufficient_evidence`       | 4    | ~33 (low)          |

The integration test `api/tests/integration/test_attribution_smoke.py`
exercises all 8 cases end-to-end via `TestClient`.

## Scoring design (WP-35 / Phase 10 + Phase 3.3)

The engine exposes two **independent** numbers per candidate — the
invariant from Phase 3.3. They are never blended into a single ranking
score.

### `proximity_rank` (Stage E) — lower is closer

A weighted-graph distance from suspect to terminal. Components:

| Component              | Default weight | When it triggers                          |
|------------------------|---------------:|-------------------------------------------|
| `base_hop_cost`        | 1.0 per hop    | always                                    |
| `mixing_penalty`       | 2.0            | path crosses a labelled mixer             |
| `bridge_penalty`       | 1.0            | path crosses a bridge contract            |
| `time_decay_penalty`   | 0–2.0          | last_seen_at older than 90 days           |
| `fan_out_penalty`      | 0–2.0          | reserved (WP-35 reserves the hook)       |

The sum is the rank. Stage G sorts ascending.

### `confidence_score` (Stage F) — 0..100

Equal-weight (1/6) combination of:

- `evidence_tier_score`       — Tier 1 → 1.0, Tier 2 → 0.8, Tier 3 → 0.55, Tier 4 → 0.3, none → 0
- `label_source_agreement`    — 1.0 if the dataset tags the terminal with a label
- `address_reuse_signal`      — `min(1.0, hops / 4)`
- `cluster_consistency`       — 1.0 for VASP-tagged terminal with no mixer hit
- `path_integrity`            — 1.0 if every hop is backed by a CanonicalTransaction
- `evidence_freshness`        — 1.0 fresh, 0.7 (<1 year), 0.4 (>1 year), 0.5 unknown

The sum × 100 is the score. Bands:

| Band    | Range    |
|---------|----------|
| high    | ≥ 70     |
| medium  | 40–69    |
| low     | < 40     |

### Mixer hard stop (Phase 14)

Any candidate that hits a labelled mixer gets
`confidence_score = 0.0` and `confidence_band = "low"` regardless of the
component weights. Mixer hits do NOT contribute to ranking — they
exist as evidence only.

### Evidence tiers (Phase 5)

| Tier | Label                                | When                                |
|------|--------------------------------------|-------------------------------------|
| 1    | Direct VASP deposit label            | VASP-tagged terminal, 1-hop, no bridge |
| 2    | Tagged hot-wallet cluster            | VASP-tagged terminal, ≤2 hops, no bridge |
| 3    | Behavioral / consolidation only      | VASP-tagged terminal that crosses a bridge |
| 4    | Heuristic / topological only         | non-VASP terminal (hub / dead end) |
| 99   | Insufficient evidence                | mixer stop or empty trail          |

### Outcome classifier

| Outcome                     | When                                      |
|-----------------------------|-------------------------------------------|
| `single_candidate`          | exactly one VASP candidate               |
| `ranked_multi_candidate`    | multiple VASP candidates                 |
| `false_candidate_filtered`  | only hubs (no mixer, no VASP)             |
| `insufficient_evidence`     | mixer hit, dead-end only, or empty        |

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