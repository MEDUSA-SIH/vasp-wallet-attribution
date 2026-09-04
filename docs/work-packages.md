# SIH26182 – Work Package / Ownership Matrix

This matrix splits the **SIH26182 backend** into discrete **work
packages (WPs)** that can be owned and developed independently. Each WP
has a single owner (or co-owners), a target branch prefix, and a short
list of touched files.

> When you start a WP, **append your GitHub handle and branch name to the
> matrix below**. When you merge, leave the matrix alone (the next person
> will overwrite your row).

---

## Status legend

- ⬜ **Unclaimed** – pick it up.
- 🟡 **In progress** – branch is open.
- ✅ **Merged into develop** – branch was merged and deleted.
- 🚫 **Blocked** – waiting on something.

---

## Matrix

| ID    | Work package                                                                                       | Owner       | Branch                              | Phase(s)         | Status |
|-------|----------------------------------------------------------------------------------------------------|-------------|-------------------------------------|------------------|--------|
| WP-01 | Scaffold (FastAPI / Docker / Alembic / docs)                                                       | @tejas      | `feat/initial-monorepo-scaffold`    | 25, 24, 8        | ✅      |
| WP-02 | Team-collab base (CI / pre-commit / contracts / docs)                                               | @tejas      | `feat/team-collab-base`             | 24               | ✅      |
| WP-03 | Bitcoin provider (live API integration)                                                            |             | `feature/btc-provider-live`         | 20               | ⬜      |
| WP-04 | Ethereum provider (live API integration)                                                           |             | `feature/eth-provider-live`         | 20               | ⬜      |
| WP-05 | TRON provider (live API integration)                                                               |             | `feature/tron-provider-live`        | 20               | ⬜      |
| WP-06 | BNB Chain provider (live API integration)                                                          |             | `feature/bnb-provider-live`         | 20               | ⬜      |
| WP-07 | Solana provider (live API integration)                                                              |             | `feature/solana-provider-live`      | 20               | ⬜      |
| WP-08 | Polygon provider (live API integration)                                                             |             | `feature/polygon-provider-live`     | 20               | ⬜      |
| WP-09 | DemoBlockchainProvider — synthetic dataset loader (CSV → CanonicalTransaction)                     |             | `feature/demo-seed-loader`          | 21, 22           | ⬜      |
| WP-10 | Attribution Stage A — discovery (seed resolution against DB)                                        |             | `feature/attr-stage-a`              | 10               | ✅ (folded into WP-35) |
| WP-11 | Synthetic dataset + offline DemoBlockchainProvider + smoke path                                     | @tejas      | `feature/synthetic-demo-provider`   | 21, 22           | 🟡 (PR open) |
| WP-12 | Attribution Stage B — graph traversal (BFS + Dijkstra)                                              |             | `feature/attr-stage-b`              | 10               | ✅ (folded into WP-35) |
| WP-13 | Attribution Stage C — filtering (VASP heuristics, dust, mixers)                                  |             | `feature/attr-stage-c`              | 10               | ✅ (folded into WP-35) |
| WP-14 | Attribution Stage D — evidence collection                                                          |             | `feature/attr-stage-d`              | 10               | ✅ (folded into WP-35) |
| WP-15 | Attribution Stage E + F — proximity + confidence scoring                                           |             | `feature/attr-stage-ef`             | 10               | ✅ (folded into WP-35) |
| WP-16 | Attribution Stage G — ranking                                                                       |             | `feature/attr-stage-g`              | 10               | ✅ (folded into WP-35) |
| WP-17 | Attribution Stage H — explainability                                                                 |             | `feature/attr-stage-h`              | 10               | ✅ (folded into WP-35) |
| WP-35 | Attribution engine core (Stages A–H end-to-end, MVP scoring) — **this stage**                       | @tejas      | `feature/attribution-engine-core`   | 10, 3.3          | 🟡 (PR open) |
| WP-18 | Graph store — Neo4j backend (replace NetworkX)                                                     |             | `feature/graph-neo4j`               | 6, 11            | ⬜      |
| WP-19 | Graph algorithms — community detection, page-rank, time-window traversal                           |             | `feature/graph-algos`               | 6, 11            | ⬜      |
| WP-20 | Risk typologies — catalog expansion (mixer, peel-chain, nested VASP, bridge abuse)                 |             | `feature/risk-typologies`           | 14               | ⬜      |
| WP-21 | Risk alerts — rule engine implementation                                                            |             | `feature/risk-alerts`               | 14               | ⬜      |
| WP-22 | Cross-chain bridge catalogue expansion + detection (Phase 13)                                       |             | `feature/cross-chain-bridges`       | 13               | ⬜      |
| WP-23 | SAHYOG adapter — real HTTP implementation                                                          |             | `feature/sahyog-real-gateway`       | 7                | ⬜      |
| WP-24 | SAHYOG inbound queue (background worker)                                                            |             | `feature/sahyog-inbound`            | 7, 23            | ⬜      |
| WP-25 | Reports — PDF / DOCX rendering (Phase 17)                                                          |             | `feature/reports-render`            | 17               | ⬜      |
| WP-26 | Evidence packaging service — Phase 16                                                               |             | `feature/evidence-package`          | 16               | ⬜      |
| WP-27 | Case service — full CRUD (Phase 12)                                                                 |             | `feature/case-crud`                 | 12               | ⬜      |
| WP-28 | Investigator service — auth, RBAC, password reset                                                  |             | `feature/auth-rbac`                 | 25               | ⬜      |
| WP-29 | Audit pipeline — middleware + persistence (Phase 25)                                                |             | `feature/audit-pipeline`            | 25               | ⬜      |
| WP-30 | Demo seed dataset (`data/synthetic/`) + reproducible CSV / parquet generator                       |             | `feature/demo-dataset`              | 21, 22           | ⬜      |
| WP-31 | Background workers — Celery / RQ setup (Phase 23)                                                  |             | `feature/worker-runtime`            | 23               | ⬜      |
| WP-32 | Observability — OpenTelemetry traces + metrics (Phase 25)                                            |             | `feature/otel`                      | 25               | ⬜      |
| WP-33 | Production deployment manifests (Helm / k8s)                                                       |             | `feature/prod-deploy`               | 24               | ⬜      |
| WP-34 | Frontend skeleton (separate repo / `packages/web/`)                                                |             | `feature/web-scaffold`              | —                | ⬜      |

---

## Coordination rules

1. **One WP per branch.** If your work spans multiple WPs, talk to the
   owners first — split the work into two PRs or take over both rows.
2. **Touch only the files in your WP**. Cross-WP edits require explicit
   approval from the affected owner(s) (see `CODEOWNERS`).
3. **Public interfaces** are frozen in `docs/contracts.md`. If a WP
   needs to change them, raise it in `#dev` first and add a
   `BREAKING CHANGE:` footer.
4. **Migrations** that touch the same table must be serialised through
   `WP-08 data team` to avoid branch conflicts.
5. **Demo data files** (`data/synthetic/*.csv`) are git-ignored once any
   are added. They live on local disk and are loaded by `WP-09` /
   `WP-30`.

---

## How to claim a WP

1. Edit this file – add your GitHub handle and the branch you created.
2. Move the status to 🟡.
3. Open the PR into `develop`.
4. When merged, move the status to ✅.

```diff
- WP-03 | Bitcoin provider (live API integration) |  | `feature/btc-provider-live` | 20 | ⬜
+ WP-03 | Bitcoin provider (live API integration) | @your-handle | `feature/btc-provider-live` | 20 | 🟡
```