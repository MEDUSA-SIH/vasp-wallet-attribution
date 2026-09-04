# SIH26182 – Architecture

The SIH26182 backend is organised as a **layered pipeline**.  Each layer
consumes the output of the layer immediately below it and exposes a
narrow surface upward.

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 8  · SAHYOG adapter (Phase 7)                              │
│  app/sahyog/{gateway,models}.py                                   │
├──────────────────────────────────────────────────────────────────┤
│  Layer 7  · Reporting (Phase 17)                                 │
│  app/services/report_service.py, app/api/v1/reports.py            │
├──────────────────────────────────────────────────────────────────┤
│  Layer 6  · Investigation / Case orchestration (Phase 12)         │
│  app/services/case_service.py, app/api/v1/cases.py               │
├──────────────────────────────────────────────────────────────────┤
│  Layer 5  · Attribution engine (Phase 10)                        │
│  app/attribution/{discovery,traversal,filtering,evidence,        │
│                   scoring,ranking,explainability,engine}.py      │
├──────────────────────────────────────────────────────────────────┤
│  Layer 4  · Graph store (Phase 6 + Phase 11)                     │
│  app/graph/{models,store,algorithms}.py                          │
├──────────────────────────────────────────────────────────────────┤
│  Layer 3  · Normalisation (Phase 9)                              │
│  app/providers/canonical.py                                      │
├──────────────────────────────────────────────────────────────────┤
│  Layer 2  · Blockchain intelligence (Phase 20)                   │
│  app/providers/{base,bitcoin,ethereum,tron,bnb,solana,polygon,   │
│                 demo}.py                                         │
├──────────────────────────────────────────────────────────────────┤
│  Layer 1  · Input (HTTP / background / SAHYOG inbound)           │
│  app/api/v1/*.py, app/workers/tasks.py                           │
└──────────────────────────────────────────────────────────────────┘
```

## Cross-cutting concerns

These concerns span every layer and live in `api/app/core/`:

- **Configuration** – `core/config.py` (pydantic-settings, `DEMO_MODE`).
- **Security** – `core/security.py` (JWT, RBAC, bcrypt).
- **Logging** – `core/logging.py` (structlog).
- **Errors** – `core/exceptions.py` (typed errors + FastAPI handlers).

## Data stores

| Store          | Role                                  | Phase | File |
|----------------|---------------------------------------|-------|------|
| PostgreSQL 16  | System of record (cases, wallets, …)  | 8     | `api/app/db/models/` |
| NetworkX       | In-process transaction graph (MVP)    | 6, 11 | `api/app/graph/store.py` |
| Redis          | Cache / queue (later stages)          | 23    | `app.state.redis` (lifespan) |

## Provider strategy (Phase 20)

Each chain has its own `BlockchainProvider` implementation:

- `BitcoinProvider`, `EthereumProvider`, `TronProvider`,
  `BnbProvider`, `SolanaProvider`, `PolygonProvider`.

They all conform to the `BlockchainProvider` ABC and normalise into the
`CanonicalTransaction` shape.  Toggle each chain individually via the
`PROVIDER_*_ENABLED` env vars.  `DemoBlockchainProvider` is always
available when `DEMO_MODE=true`.

## Attribution pipeline (Phase 10)

The engine runs eight stages (A→H).  Each stage is a separate function so
they can be unit-tested and replaced independently:

| Stage | Module                              | Purpose |
|-------|-------------------------------------|---------|
| A     | `attribution/discovery.py`          | resolve seed addresses |
| B     | `attribution/traversal.py`          | BFS/Dijkstra expansion |
| C     | `attribution/filtering.py`          | drop low-signal candidates |
| D     | `attribution/evidence.py`           | assemble evidence snippets |
| E     | `attribution/scoring.py`            | proximity scoring |
| F     | `attribution/scoring.py`            | confidence combination |
| G     | `attribution/ranking.py`            | ranked output |
| H     | `attribution/explainability.py`     | per-wallet rationale |

## Deployment (Phase 24)

The local stack is `docker compose` with three services:

- `postgres` (postgres:16-alpine, named volume `sih26182_pgdata`),
- `redis` (redis:7-alpine, named volume `sih26182_redisdata`),
- `api` (multi-stage Dockerfile, non-root user, healthcheck on
  `/api/v1/health`).

Production deploys are out of scope for Stage 0; see `docs/development.md`
for the local dev workflow.

## Design decisions made in Stage 0

These decisions were not explicitly covered by the prompt or the spec
and are recorded here so they can be reviewed later.

1. **`Database` URL is composed** in `Settings` (computed field) rather
   than read directly from `DATABASE_URL` so it stays consistent with
   `POSTGRES_*` individual vars.
2. **`CanonicalTransaction`** is re-exported through both
   `app.providers.canonical` (canonical location) and `app.providers`
   (top-level re-export) so old imports keep working if a future refactor
   moves the definition.
3. **`ProviderRegistry`** lives next to the ABC so it can be wired into
   the lifespan (later stages) without a service-locator dependency.
4. **Phase-8 ORM relationships are not declared yet** to keep models
   importable independently.  Relationships will be added in the next
   stage when query paths are wired.