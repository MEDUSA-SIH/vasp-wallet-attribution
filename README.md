# SIH26182 – VASP Wallet Attribution

> Smart India Hackathon 2026 · Problem Statement **SIH26182**
> Cross-chain wallet attribution engine for Indian Law Enforcement Agencies (LEAs).

## What is this?

This monorepo hosts the backend services for **SIH26182** — a system that
helps Indian LEAs attribute pseudonymous blockchain wallets to **VASPs
(Virtual Asset Service Providers)** such as Indian and international
exchanges. It ingests transactions from multiple chains (BTC, ETH, TRX,
BNB, SOL, MATIC), builds a multi-chain transaction graph, runs an
attribution engine, and produces structured evidence packages that can be
routed through the **SAHYOG** inter-agency gateway.

> **Stage 0 status — Scaffold complete · business logic pending**
>
> The repository layout, interfaces, configuration, Docker Compose stack
> and Alembic migrations are in place. Provider integrations, attribution
> scoring, risk typologies and SAHYOG adapters are scaffolded but not yet
> implemented. See `docs/phases-mapping.md` to map folders to the SIH26182
> specification phases.

## Repository layout

```
sih26182-vasp-attribution/
├── api/                 # FastAPI service (main backend)
├── packages/common/      # Shared Python types (optional shared library)
├── data/synthetic/      # Offline demo dataset (Phase 21/22)
├── docs/                # Architecture & phase mapping
├── scripts/             # Developer convenience scripts
├── docker-compose.yml   # postgres + redis + api
├── Makefile             # Common tasks
└── .env.example         # Environment variable template
```

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/api/v1/health
```

The API will respond with:

```json
{ "status": "ok", "demo_mode": true, "version": "0.1.0" }
```

## Quick start (local Python)

```bash
cd api
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Useful Make targets

| Target          | What it does                          |
|-----------------|---------------------------------------|
| `make up`       | Bring the full stack up               |
| `make down`     | Stop the stack                        |
| `make logs`     | Tail api logs                         |
| `make migrate`  | Apply Alembic migrations              |
| `make test`     | Run pytest                            |
| `make lint`     | Run ruff                              |
| `make shell`    | Open a shell inside the api container |
| `make seed-demo`| Load the offline demo dataset (later)   |

## Documentation

- `docs/architecture.md`  – layered architecture overview.
- `docs/phases-mapping.md` – mapping of every folder to the SIH26182 spec phases.
- `docs/development.md`   – developer setup, lint/test workflow.

## License

Proprietary – Smart India Hackathon 2026 submission.