# SIH26182 — VASP Wallet Attribution

> **Smart India Hackathon 2026 · Problem Statement SIH26182** — Sponsoring Organisation: **Ministry of Home Affairs (MHA), Indian Cyber Crime Coordination Centre (I4C), CIS Division**
>
> Cross-chain attribution engine that traces suspect cryptocurrency wallets to their nearest **VASP** (Virtual Asset Service Provider — exchanges, custodial wallet providers, brokers) across Bitcoin, Ethereum, Tron, BNB Chain, Solana and Polygon, and routes lawful disclosure requests via the **SAHYOG** inter-agency gateway.

[![CI](https://github.com/MEDUSA-SIH/vasp-wallet-attribution/actions/workflows/ci.yml/badge.svg)](https://github.com/MEDUSA-SIH/vasp-wallet-attribution/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](api/pyproject.toml)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-lightgrey.svg)](#license)

---

## Table of Contents

- [Overview](#overview)
- [Key Capabilities](#key-capabilities)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Repository Layout](#repository-layout)
- [How the Code is Organized](#how-the-code-is-organized)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Offline Demo — 8 Synthetic Cases](#offline-demo--8-synthetic-cases)
- [API Reference](#api-reference)
- [Testing, Linting, Migrations](#testing-linting-migrations)
- [Documentation Map](#documentation-map)
- [Security](#security)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

Indian Law Enforcement Agencies (LEAs) routinely encounter **pseudonymous, unhosted wallets** linked to fraud, ransomware, investment scams, and laundering. Today an investigator must manually follow a wallet's fund flows hop-by-hop across multiple block explorers, check each address against tribal knowledge of exchange wallets, and assemble a disclosure request — a process measured in hours to days. The result is inconsistent attribution, weak evidentiary trails, and missed windows for asset freezing.

This repository implements the backend for **SIH26182**: an automated, explainable, multi-chain attribution system that:

1. **Ingests** a suspect wallet address (from SAHYOG or direct API).
2. **Traces** its transaction graph across supported chains via a uniform `BlockchainProvider` abstraction.
3. **Discovers** the nearest VASP-controlled deposit address by directed graph distance, not by geography or volume.
4. **Scores** each candidate with two independent numbers — *proximity rank* (how close) and *confidence score* with an *evidence tier* (how credible) — and never blends them.
5. **Explains** every candidate in plain language and produces an investigation-ready evidence package.
6. **Routes** the analyst-approved disclosure / freeze request back through SAHYOG to the correct legal entity.

The system is **offline-first**: with `DEMO_MODE=true` (the default) the entire pipeline runs against a deterministic synthetic dataset without live chain API keys, so every contributor and reviewer can reproduce attribution end-to-end.

> **Current maturity: Stage 1 + Stage 2 on `main`/`develop` (`ab48ae1`)**
>
> | Milestone | What landed | Docs |
> |-----------|-------------|------|
> | **Stage 0** — Scaffold | FastAPI service, Docker Compose (postgres 16 + redis 7 + api), Alembic migrations, layered folder structure | `docs/architecture.md`, `docs/phases-mapping.md` |
> | **Stage 0.5** — Team base | CI (`lint` · `import smoke` · `pytest`), pre-commit (ruff), frozen contracts, work-package matrix, CODEOWNERS | `CONTRIBUTING.md`, `docs/work-packages.md` |
> | **Stage 1** — Synthetic offline demo | `data/synthetic/` — 8 synthetic cases; `DemoBlockchainProvider`; DEMO_MODE-aware `ProviderRegistry`; `POST /api/v1/attribution/run` smoke endpoint; `make seed-demo` idempotent loader | `docs/development.md` |
> | **Stage 2** — Attribution engine core | 8-stage pipeline **A→H** with proximity + confidence scoring, outcome classifier, and plain-language explanations | `docs/development.md` |
>
> CI is green on `main` and `develop`: `ruff check`, `ruff format --check`, `import smoke` (5 modules), `pytest` (66 tests). See [Quick Start](#quick-start) to run the demo locally.

---

## Key Capabilities

- **Multi-chain by design.** Six chains today (BTC, ETH, TRON, BNB, SOL, POLYGON) via a single `BlockchainProvider` ABC (`api/app/providers/base.py`). Adding a chain is an adapter, not a rewrite (see `docs/phases-mapping.md`, Phase 20, REQ-007).
- **Deterministic offline demo.** `DEMO_MODE=true` serves all 8 synthetic patterns through the same interface as live providers — reviewers need no API keys.
- **Explainable attribution.** The 8 steps (discovery → traversal → filtering → evidence → proximity → confidence → ranking → explainability) are isolated, unit-tested functions. Proximity and confidence are *independent*, and every candidate carries an `evidence_tier` and a plain-language `explanation`.
- **Evidence-first.** The demo path is also a smoke test: `api/tests/integration/test_attribution_smoke.py` exercises all 8 cases; `POST /api/v1/attribution/run` returns `outcome` + `insufficient_evidence` instead of guessing. Mixer hits trigger a hard stop.
- **LEA-ready seams.** SAHYOG gateway (`app/sahyog/gateway.py`), case management, graph store, and report rendering are present as typed stubs with frozen contracts (`docs/contracts.md`).

---

## Architecture at a Glance

```
Layer 8  SAHYOG adapter          app/sahyog/{gateway,models}.py            Phase 7
Layer 7  Reporting               app/services/report_service.py               Phase 17
Layer 6  Investigation / Cases   app/services/case_service.py                 Phase 12
Layer 5  Attribution engine      app/attribution/{discovery,…,explainability} Phase 10 (Stages A–H)
Layer 4  Graph store             app/graph/{models,store,algorithms}.py       Phase 6 + 11
Layer 3  Normalisation           app/providers/canonical.py                   Phase 9
Layer 2  Blockchain intel        app/providers/{base,bitcoin,…,demo}.py       Phase 20
Layer 1  Input                   app/api/v1/*.py, app/workers/tasks.py        Phase 23/25
         ─────────────────────────────────────────────────────────────────────────
Cross-cutting:  app/core/{config,security,logging,exceptions}.py              Phase 25
Data:           PostgreSQL 16 (system of record, Phase 8) · NetworkX (MVP graph) · Redis (cache/queue, Phase 23)
```

Full diagram and design decisions: [`docs/architecture.md`](docs/architecture.md).

---

## Repository Layout

```
sih26182-vasp-attribution/
├── api/                  # FastAPI service — the only deployable
│   ├── app/
│   │   ├── api/v1/       # HTTP routers (health, attribution, cases, wallets, reports, admin)
│   │   ├── attribution/  # 8-stage engine: discovery, traversal, filtering, evidence,
│   │   │                 # scoring (E/F), ranking (G), explainability (H), types
│   │   ├── core/         # config, security (JWT/bcrypt/RBAC), logging, exceptions
│   │   ├── cross_chain/  # bridge catalogue (Phase 13)
│   │   ├── db/           # SQLAlchemy models + Alembic migrations (Phase 8)
│   │   ├── graph/        # NetworkX store + algorithms (Phase 6)
│   │   ├── providers/    # BlockchainProvider ABC, per-chain stubs, demo provider (Phase 20–22)
│   │   ├── risk/         # typologies & alerts
│   │   ├── sahyog/       # SAHYOG gateway adapter (Phase 7)
│   │   ├── schemas/      # Pydantic request/response models
│   │   ├── services/     # Orchestration (attribution_service, etc.)
│   │   └── workers/      # Background tasks (Phase 23)
│   ├── alembic/          # Migrations (0001_initial declares all tables)
│   ├── scripts/          # seed_demo_data, create_db
│   ├── tests/            # unit + integration (pytest, 66 tests)
│   ├── Dockerfile        # multi-stage, non-root, healthcheck on /api/v1/health
│   └── pyproject.toml    # service dependencies (hatchling)
├── packages/common/      # Shared Python types (ChainCode, etc.)
├── data/synthetic/       # Offline demo dataset — 8 JSON cases (Phase 21/22)
├── docs/                 # Architecture, contracts, phases, work-packages, glossary
├── scripts/              # bootstrap.sh, check.sh
├── .github/              # CI, issue/PR templates, CODEOWNERS, ruleset
├── docker-compose.yml    # postgres + redis + api (local dev)
├── Makefile              # make up/down/logs/migrate/test/lint/format/check/seed-demo/branch
├── pyproject.toml        # workspace lint config (ruff)
├── .env.example          # environment template (never commit real .env)
├── CONTRIBUTING.md       # branching, Conventional Commits, PR checklist
├── SECURITY.md           # private disclosure policy, threat model, secure coding
└── SIH26182_Technical_Specification.md  # upstream PS research & phase catalogue
```

Every folder → SIH phase mapping: [`docs/phases-mapping.md`](docs/phases-mapping.md).

---

## How the Code is Organized

The attribution engine runs in 8 simple steps, each in its own file:

| Step | File | What it does |
|------|------|--------------|
| **A — Discovery** | `attribution/discovery.py` | Finds candidate wallets by walking the transaction graph |
| **B — Traversal** | `attribution/traversal.py` | Rebuilds the full path for each candidate |
| **C — Filtering** | `attribution/filtering.py` | Removes noise (dust, duplicates, hubs) |
| **D — Evidence** | `attribution/evidence.py` | Gathers supporting evidence |
| **E — Proximity** | `attribution/scoring.py` | Scores how close each candidate is |
| **F — Confidence** | `attribution/scoring.py` | Scores how trustworthy each match is |
| **G — Ranking** | `attribution/ranking.py` | Sorts by proximity and picks the outcome |
| **H — Explanation** | `attribution/explainability.py` | Writes a plain-English explanation |

The offline demo dataset (`data/synthetic/`, 8 test cases) lets the whole pipeline run without live blockchain APIs. When `DEMO_MODE` is on, the app uses the demo data; when off, it will use real chain providers.

See [`docs/architecture.md`](docs/architecture.md) for the full layered view and [`docs/glossary.md`](docs/glossary.md) for a plain-language glossary of terms like VASP, mixer, bridge, and evidence tiers.

---

## Requirements

### System requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **OS** | Linux (Ubuntu 22.04+), macOS 13+, or Windows 11 + WSL2 | Ubuntu 22.04 LTS | Docker Desktop required on macOS/Windows |
| **CPU / RAM** | 2 vCPU / 4 GB RAM | 4 vCPU / 8 GB RAM | Attribution engine is CPU-bound; graph traversal benefits from extra RAM |
| **Disk** | 10 GB free | 20 GB free | Includes Docker images, Postgres data, and synthetic dataset |
| **Python** | **3.12** (as used in CI) | 3.12.x | 3.11 works for docs only; tests and production target 3.12 |
| **Docker** | Engine 24+ + Compose v2 | Latest stable | Required for `postgres:16-alpine` + `redis:7-alpine` + API container |
| **Network** | Outbound HTTPS (for `pip`/`uv`) | — | No live blockchain API needed in `DEMO_MODE=true` |

### Software prerequisites

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| `git` | 2.40+ | Clone & branch | `sudo apt install git` / `brew install git` |
| `docker` + `docker compose` | Engine 24+, Compose v2 | Run the full stack | <https://docs.docker.com/get-docker/> |
| `python` | 3.12 | Local runs & CI | <https://www.python.org/downloads/> or `uv python install 3.12` |
| `uv` | 0.4+ (optional but recommended) | Fast installs, venv, lockfile | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `make` | 4.3+ | Shortcuts (`make up`, `make test`, …) | `sudo apt install make` / Xcode CLT on macOS |

Verify once:

```bash
python3 --version   # → Python 3.12.x
docker --version    # → Docker version 24+
docker compose version  # → v2.x
uv --version       # optional
make --version
```

### Environment template

Copy and edit the env file **before** first run. Never commit the real `.env`.

```bash
cp .env.example .env
# Edit .env if needed — defaults are safe for demo (DEMO_MODE=true,
# postgres on localhost:5432, redis on localhost:6379)
```

See [Configuration](#configuration) for the full variable list.

---

## Quick Start

### Option A — Docker Compose (recommended, one command)

```bash
cp .env.example .env          # skip if already done
docker compose up -d --build
docker compose exec api alembic upgrade head   # or: make migrate
curl http://localhost:8000/api/v1/health
# {"status":"ok","demo_mode":true,"version":"0.1.0"}
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs` · Health: `GET /api/v1/health`

Tear down when done: `docker compose down` or `make down`.

### Option B — Local Python (API outside Docker, DB still in Docker)

```bash
# 1. Start only the data services
docker compose up -d postgres redis

# 2. Run the API locally
cd api
uv venv --python 3.12
uv pip install -e ".[dev]"
cp ../.env.example .env       # ensure POSTGRES_HOST=localhost, REDIS_HOST=localhost
uvicorn app.main:app --reload --port 8000
# or: python -m uvicorn app.main:app --reload

# 3. In another terminal, apply migrations and check health
curl http://localhost:8000/api/v1/health
```

### Verify the setup

```bash
curl -s http://localhost:8000/api/v1/health | jq
# {"status":"ok","demo_mode":true,"version":"0.1.0"}

# Run the full offline demo (no API keys) — see next section
curl -s -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case1_suspect_001","chain":"ethereum"}' | jq '.outcome'
# "single_candidate"
```

If either check fails, see `make logs` (Docker) or `uvicorn` output (local) and `docs/development.md`.

Common ports used: **8000** (API), **5432** (Postgres), **6379** (Redis). Override in `.env` if occupied.

---

## Configuration

All settings are loaded via `pydantic-settings` from environment variables / `.env` (`api/app/config.py`, Phase 25). Never commit a real `.env`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEMO_MODE` | `true` | **Offline demo toggle**. When `true`, the app uses the local demo dataset for every chain (no API keys). When `false`, per-chain stubs raise an error until real chain integrations are added. |
| `SECRET_KEY` | `change-me` | JWT signing key — override in every non-demo deployment. |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `localhost` / `5432` / `sih26182` / `sih26182` / `sih26182` | Postgres connection (Phase 8). `docker compose` sets host to `postgres` automatically. |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | Redis (Phase 23). |
| `ATTRIBUTION_MAX_HOPS` | `5` | BFS budget for the attribution engine (Phase 10). |

See [`.env.example`](.env.example) for the full list.

---

## Offline Demo — 8 Synthetic Cases

With `DEMO_MODE=true` the synthetic dataset under `data/synthetic/` is queryable through the same `BlockchainProvider` interface as real chains. No live explorer keys are needed.

### Seed (idempotent)

```bash
make seed-demo
# or: cd api && python -m scripts.seed_demo_data
```

The seed is best-effort with respect to the DB: it always loads the in-memory demo indexes, and additionally upserts to Postgres when reachable.

### Run attribution

```bash
# Case 1 — direct VASP deposit → single_candidate, Tier 1, high confidence
curl -s -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case1_suspect_001","chain":"ethereum"}' | jq

# Case 5 — mixer hit → insufficient_evidence, confidence 0 (Phase 14 hard stop)
curl -s -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case5_suspect_001","chain":"ethereum"}' | jq
```

All 8 patterns (see [`docs/development.md#offline-demo-path`](docs/development.md) and the integration test `api/tests/integration/test_attribution_smoke.py`):

| Case | Pattern | Expected `outcome` | Tier | Confidence |
|------|---------|-------------------|------|------------|
| 1 | Direct VASP deposit | `single_candidate` | 1 | ~78 high |
| 2 | One intermediary | `single_candidate` | 2 | ~78 high |
| 3 | Multiple intermediaries | `single_candidate` | 3 | ~82 high |
| 4 | Multiple candidate VASPs | `ranked_multi_candidate` | 2 | ~78 high |
| 5 | Mixer | `insufficient_evidence` | 99 | 0.0 low |
| 6 | Bridge (cross-chain) | `single_candidate` | 3 | ~74 high |
| 7 | False candidate (high-degree hub) | `false_candidate_filtered` | 4 | ~49 medium |
| 8 | Ambiguous / insufficient | `insufficient_evidence` | 4 | ~33 low |

### How scoring works

Two independent numbers per candidate — never blended:

- **`proximity_rank`** — how close the candidate is (lower is closer): based on hops plus penalties for mixers, bridges, and old activity. The ranking step sorts by this.
- **`confidence_score`** — 0–100, how trustworthy the match is: average of 6 simple signals (evidence tier, label agreement, address reuse, cluster consistency, path integrity, freshness). Bands: `high` ≥70, `medium` 40–69, `low` <40. Mixer hits are stopped to `0.0`/`low`.

See [`docs/development.md`](docs/development.md) for the full breakdown.

---

## API Reference

All routes are under `/api/v1` (see `docs/contracts.md §7` — frozen surface).

| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| `GET` | `/api/v1/health` | 25 | Liveness: `{status, demo_mode, version}` |
| `POST` | `/api/v1/attribution/run` | 10 | **Smoke endpoint** — run the 8-stage engine against the demo (or real) providers. Body: `{suspect_address, chain, case_id?, max_hops?}`. Returns `AttributionRunResult` with `outcome`, `candidates[]`, `explanations{}` |
| `GET`/`POST` | `/api/v1/cases` | 12 | Case CRUD (stub) |
| `GET` | `/api/v1/cases/{case_id}` | 12 | Fetch case |
| `GET`/`POST` | `/api/v1/wallets` | 11 | Wallet / graph queries (stub) |
| `GET` | `/api/v1/wallets/{wallet_id}` | 11 | Fetch wallet |
| `POST` | `/api/v1/reports/generate` | 17 | Report rendering (stub) |
| `GET` | `/api/v1/admin/settings` | 25 | Echo resolved settings (non-secret fields) |

Interactive docs when the API is running: `http://localhost:8000/docs` (Swagger) and `/redoc`.

---

## Testing, Linting, Migrations

| Task | Command | Notes |
|------|---------|-------|
| Bring stack up | `make up` | `docker compose up -d --build` |
| Tail API logs | `make logs` | `docker compose logs -f api` |
| Open API shell | `make shell` | `docker compose exec api bash` |
| Apply migrations | `make migrate` | `docker compose exec api alembic upgrade head` |
| New migration | `make revision m="add foo"` | Generates `api/alembic/versions/NNNN_*.py` |
| Run tests | `make test` | `docker compose exec api pytest` (or `uv run pytest api/tests -q` locally) |
| Lint | `make lint` | `ruff check api/ packages/` |
| Format | `make format` | `ruff format api/ packages/` |
| Quick sanity | `make check` | `scripts/check.sh` — ruff + import smoke + yaml sanity |
| Seed demo | `make seed-demo` | `docker compose exec api python -m scripts.seed_demo_data` |
| Pre-commit | `make install-hooks` · `make pre-commit` | `ruff` + `gitleaks` hooks |

CI (`.github/workflows/ci.yml`) runs three jobs on every push/PR to `main`/`develop`: `Lint (ruff)`, `Import smoke (app can boot)`, `Tests (pytest)` with postgres 16 + redis 7 services. All three must be green before merge.

---

## Documentation Map

| Doc | What it answers |
|-----|-----------------|
| [`docs/architecture.md`](docs/architecture.md) | Layered pipeline (8 layers), cross-cutting concerns, data stores, provider strategy, attribution pipeline A→H, deployment |
| [`docs/phases-mapping.md`](docs/phases-mapping.md) | Folder → Phase mapping for the entire repo (Phase 1–26) |
| [`docs/contracts.md`](docs/contracts.md) | **Frozen** public interfaces — `BlockchainProvider`, `CanonicalTransaction`, `AttributionEngine`, `GraphStore`, `SahyogGateway`, `Settings`, routers, ORM, migrations, shared types |
| [`docs/work-packages.md`](docs/work-packages.md) | Ownership matrix — which WP owns which phases/files/branch/status (start here to claim work) |
| [`docs/development.md`](docs/development.md) | Day-to-day setup, offline demo walkthrough, scoring design, how to add a model/provider |
| [`docs/glossary.md`](docs/glossary.md) | **Glossary of Phase / Stage / WP / chain / evidence-tier terminology** — read this first if W-11 / Phase 10 / Stage A mean nothing yet |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branching model, workflow, Conventional Commits, PR checklist, code style |
| [`SECURITY.md`](SECURITY.md) | Private disclosure, supported versions, threat model, secure coding, dependency & secrets handling |
| [`SIH26182_Technical_Specification.md`](SIH26182_Technical_Specification.md) | Upstream PS research, requirement catalogue (REQ-001…030), and scoring / VASP intelligence design |

---

## Security

See [`SECURITY.md`](SECURITY.md) for the full policy. **Do not file a public issue for a suspected vulnerability** — email the maintainers in [`.github/CODEOWNERS`](.github/CODEOWNERS) or open a private GitHub Security Advisory. We acknowledge within 2 business days and aim to ship a fix for high-severity issues within 7 days.

If you are deploying beyond the demo, override `SECRET_KEY`, set `DEMO_MODE=false`, and provide real chain provider credentials — the scaffold defaults are not safe for public networks.

---

## Contributing

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/work-packages.md`](docs/work-packages.md) before opening a PR.

- Pick an unclaimed WP, add your handle + branch to the matrix, and open your PR into `develop`.
- Keep PRs within a single WP; cross-WP edits need owner approval (`CODEOWNERS`).
- Public interfaces are frozen in `docs/contracts.md` — breaking changes need a `BREAKING CHANGE:` footer and a heads-up in `#dev`.
- Every PR must pass `ci` (lint + import smoke + pytest) and update docs when behaviour changes.

---

## Roadmap

| Milestone | Scope | Status |
|-----------|-------|--------|
| Stage 0 + 0.5 | Scaffold + team base | ✅ on `main`/`develop` (`ab48ae1`) |
| Stage 1 + Stage 2 | Offline demo + attribution engine A–H | ✅ |
| Stage 3 | Live chain adapters, SAHYOG real gateway, graph-neo4j, reports, risk typologies | ⬜ next |
| Stage 4 | Workers, observability, hardening & production manifests | Planned |

See `docs/work-packages.md` for the full WP matrix and current ownership.

---

## License

Proprietary — Smart India Hackathon 2026 submission. All rights reserved. No license is granted for reuse outside the SIH evaluation context.

---

## Acknowledgements

Problem statement and sponsorship: **Ministry of Home Affairs, I4C, CIS Division** via SIH 2026. Built by the **MEDUSA** team. Off-chain intelligence patterns and VASP/Tier definitions are informed by public FATF/PMLA guidance and commercial blockchain-intelligence research, adapted into an explainable MVP for LEA use.

