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

> **Stage 1 status – Synthetic dataset + offline DemoBlockchainProvider merged on `develop`**
>
> The repository layout, interfaces, configuration, Docker Compose stack
> and Alembic migrations are in place, plus the team-collaboration base
> (CI, pre-commit, contracts doc, work-package matrix, CODEOWNERS) and
> the offline attribution path:
>
> - `data/synthetic/` – 8 synthetic test cases (Phase 22 patterns).
> - `app/providers/demo.py` – `DemoBlockchainProvider` serves them.
> - `app/providers/factory.py` – DEMO_MODE-aware provider registry.
> - `app/services/attribution_service.py` + `POST /api/v1/attribution/run`
>   – the smoke endpoint that walks the demo graph end-to-end.
> - `make seed-demo` – idempotent seed script.
>
> See `docs/phases-mapping.md` to map folders to the SIH26182 phases,
> `docs/work-packages.md` to claim a slice of the work, and
> `docs/development.md` for the offline-demo walk-through.

## Repository layout

```
sih26182-vasp-attribution/
├── api/                 # FastAPI service (main backend)
├── packages/common/      # Shared Python types
├── data/synthetic/      # Offline demo dataset (Phase 21/22)
├── docs/                # Architecture, contracts, phases, work packages
├── scripts/             # bootstrap.sh / check.sh
├── .github/             # CI, PR/Issue templates, CODEOWNERS
├── docker-compose.yml   # postgres + redis + api
├── Makefile             # Common tasks
├── CONTRIBUTING.md      # Branching & PR workflow
└── .env.example             # Environment variable template
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

## Team workflow

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) – branching model,
   Conventional Commits, PR checklist.
2. Pick a work package from [`docs/work-packages.md`](docs/work-packages.md)
   and claim it.
3. Install pre-commit hooks once:
   ```bash
   pip install pre-commit
   pre-commit install
   ```
4. Branch off `develop` and open your PR.

```bash
make branch NAME=btc-provider-live   # creates feature/btc-provider-live
make check                          # runs ruff + import smoke + yaml sanity
make test                           # runs pytest
make migrate                        # applies Alembic migrations
make seed-demo                      # loads data/synthetic/ into the demo provider
```

## Offline demo (Phase 21 / 22)

Once the stack is up (with `DEMO_MODE=true`, the default), the synthetic
dataset is queryable through the same `BlockchainProvider` interface as
real chains:

```bash
# Case 1 — direct VASP deposit
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case1_suspect_001","chain":"ethereum"}'

# Case 5 — mixer → insufficient_evidence
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case5_suspect_001","chain":"ethereum"}'
```

All 8 cases (see `docs/development.md`) resolve to their documented
outcome without any live API keys.

## Useful Make targets

| Target                | What it does                              |
|-----------------------|-------------------------------------------|
| `make up`             | Bring the full stack up                   |
| `make down`           | Stop the stack                            |
| `make logs`           | Tail api logs                             |
| `make migrate`        | Apply Alembic migrations                  |
| `make test`           | Run pytest                                |
| `make lint`           | Run ruff                                  |
| `make format`         | Run ruff format                           |
| `make shell`          | Open a shell inside the api container     |
| `make seed-demo`      | Load the offline demo dataset (later)     |
| `make install-hooks`  | Install pre-commit hooks                  |
| `make check`          | Run scripts/check.sh                      |
| `make branch NAME=x`  | Create a feature branch off develop       |
| `make revision m=...` | Generate an Alembic migration             |

## Documentation

- `docs/architecture.md`    – layered architecture overview.
- `docs/phases-mapping.md`  – mapping of every folder to the SIH26182 spec phases.
- `docs/contracts.md`       – **frozen** public interfaces.
- `docs/work-packages.md`   – ownership matrix for parallel work.
- `docs/development.md`     – developer setup, lint/test workflow.
- `CONTRIBUTING.md`         – branching + PR workflow.

## License

Proprietary – Smart India Hackathon 2026 submission.