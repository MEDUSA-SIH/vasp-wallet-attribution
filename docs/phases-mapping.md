# SIH26182 – Phases mapping

The SIH26182 Technical Specification is structured in numbered "phases".
This document maps every folder in the repository to the phase(s) it
implements so future agents (and humans) can navigate the codebase without
re-reading the spec.

| Folder / File                                              | Spec phase(s)               | Notes |
|------------------------------------------------------------|----------------------------|-------|
| `api/app/main.py`                                          | 25 (App framework)         | FastAPI factory, lifespan, CORS, exception handlers |
| `api/app/config.py`                                        | 25                         | pydantic-settings, DEMO_MODE flag |
| `api/app/dependencies.py`                                  | 25                         | FastAPI Depends helpers |
| `api/app/core/security.py`                                 | 25                         | bcrypt + JWT + RBAC stubs |
| `api/app/core/logging.py`                                  | 25                         | structlog |
| `api/app/core/exceptions.py`                               | 25                         | custom error types & handlers |
| `api/app/db/base.py`, `api/app/db/session.py`              | 8                          | Declarative base, async session factory |
| `api/app/db/models/*.py`                                   | 8                          | SQLAlchemy ORM mirroring the Phase 8 DDL |
| `api/alembic/`, `api/alembic.ini`                          | 8                          | Migrations (initial scaffold) |
| `api/alembic/versions/0001_initial.py`                     | 8                          | First migration declaring all tables |
| `api/app/schemas/*.py`                                     | 12, 11, 10, 17             | Pydantic request/response models |
| `api/app/graph/models.py`, `api/app/graph/store.py`       | 6                          | Node/edge types + NetworkX store |
| `api/app/graph/algorithms.py`                              | 6, 11                      | BFS, Dijkstra, clustering stubs |
| `api/app/providers/base.py`, `api/app/providers/canonical.py` | 9, 20                   | Provider abstraction + CanonicalTransaction |
| `api/app/providers/demo.py`                                | 21, 22                     | Offline demo provider |
| `api/app/providers/{bitcoin,ethereum,tron,bnb,solana,polygon}.py` | 20                   | Per-chain stubs |
| `api/app/attribution/engine.py`                            | 10                         | Orchestrator (stages A→H) |
| `api/app/attribution/{discovery,traversal,filtering,evidence,scoring,ranking,explainability}.py` | 10         | Stage A–H placeholders |
| `api/app/risk/{typology,alerts}.py`                        | 14 (+ REQ-020–023)         | Risk typology catalog + alert evaluation |
| `api/app/cross_chain/bridges.py`                           | 13                         | Cross-chain bridge catalog |
| `api/app/sahyog/{gateway,models}.py`                       | 7                          | SAHYOG adapter interface |
| `api/app/services/*.py`                                    | 10, 12, 16, 17             | Higher-level orchestration |
| `api/app/api/v1/*.py`                                      | 25                         | HTTP routers (cases, wallets, attribution, reports, admin, health) |
| `api/app/workers/tasks.py`                                 | 23                         | Background task stubs |
| `api/scripts/seed_demo_data.py`                            | 21, 22                     | Synthetic data loader |
| `api/scripts/create_db.py`                                 | 8                          | DB bootstrap helper |
| `packages/common/src/common/types.py`                      | 20, 26                     | Cross-monorepo types |
| `data/synthetic/`                                          | 21, 22                     | Offline demo dataset |
| `docker-compose.yml`, `api/Dockerfile`                     | 24 (deployment)           | Local dev stack |
| `scripts/bootstrap.sh`, `scripts/check.sh`                 | 24                         | Convenience scripts |

## How to read this table

- **Phase 1–5** – Problem framing and design → captured in
  `SIH26182_Technical_Specification.md` (the upstream spec).
- **Phase 6** – Multi-chain graph model → `api/app/graph/`.
- **Phase 7** – SAHYOG inter-agency adapter → `api/app/sahyog/`.
- **Phase 8** – Relational schema → `api/app/db/models/` + Alembic.
- **Phase 9** – Canonical transaction schema → `api/app/providers/canonical.py`.
- **Phase 10** – Attribution engine → `api/app/attribution/`.
- **Phase 11** – Graph store and wallet APIs → `api/app/graph/`,
  `api/app/api/v1/wallets.py`.
- **Phase 12** – Case management → `api/app/api/v1/cases.py`,
  `api/app/services/case_service.py`.
- **Phase 13** – Cross-chain bridges → `api/app/cross_chain/`.
- **Phase 14** – Risk typologies → `api/app/risk/`.
- **Phase 16** – Evidence packaging → `api/app/services/evidence_service.py`.
- **Phase 17** – Reporting → `api/app/services/report_service.py`,
  `api/app/api/v1/reports.py`.
- **Phase 20** – Provider abstraction → `api/app/providers/`.
- **Phase 21–22** – Demo mode & synthetic dataset → `api/app/providers/demo.py`,
  `api/scripts/seed_demo_data.py`, `data/synthetic/`.
- **Phase 23** – Background workers → `api/app/workers/`.
- **Phase 24** – Deployment / Docker → `docker-compose.yml`, `Dockerfile`,
  `Makefile`, `scripts/`.
- **Phase 25** – Application framework & security → `api/app/main.py`,
  `api/app/core/`, `api/app/api/`.
- **Phase 26** – Tooling & decisions (locked tech stack) → `pyproject.toml`,
  this mapping doc.

Any deviation from this mapping is recorded in `docs/architecture.md`.