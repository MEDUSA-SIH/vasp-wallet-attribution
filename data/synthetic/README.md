# Synthetic dataset (Phase 22)

Offline demo dataset for the SIH26182 attribution pipeline. All addresses,
names and identifiers are **obviously fake** — they are not real exchange
names or mainnet addresses. The prefix `0xDEMO_…`, `DEMOcase…`, `TDEMO…`,
`DEMOSOL…` makes them distinguishable at a glance.

## What's in here

| File              | Purpose                                                   |
|-------------------|-----------------------------------------------------------|
| `cases.json`      | The 8 synthetic test cases and expected outcomes          |
| `addresses.json`  | All addresses with chain, role, label, VASP/mixer/bridge id |
| `transactions.json` | Canonical transactions (Phase 9 shape) for every hop    |
| `vasps.json`      | Fake VASP entities (no real exchange names)               |
| `bridges.json`    | Fake cross-chain bridge contracts                         |
| `mixers.json`     | Fake mixer addresses                                      |

## The 8 patterns (Phase 22)

| Case | Pattern                          | Expected outcome                       |
|------|----------------------------------|----------------------------------------|
| 1    | Direct VASP deposit              | `single_candidate`                     |
| 2    | One intermediary                 | `single_candidate`                     |
| 3    | Multiple intermediaries          | `single_candidate_with_decay`          |
| 4    | Multiple candidate VASPs         | `ranked_multi_candidate`               |
| 5    | Mixer                            | `insufficient_evidence`                |
| 6    | Bridge (cross-chain)             | `single_candidate_with_bridge_decay`   |
| 7    | False candidate (high-degree)    | `false_candidate_filtered`             |
| 8    | Ambiguous / insufficient         | `insufficient_evidence`                |

## Loading

```bash
# From repo root:
docker compose exec api python -m scripts.seed_demo_data

# Or, locally:
cd api
PYTHONPATH=. python -m scripts.seed_demo_data
```

The seed script:

1. Reads every JSON file in this directory.
2. Builds the `NetworkX` graph store in-process.
3. (Optionally) upserts VASP + address rows in Postgres — only when a
   real `DATABASE_URL` is reachable.

It is **idempotent** — running it twice is safe.

## How a developer runs the smoke path

```bash
# 1. Activate demo mode and start the stack
export DEMO_MODE=true
docker compose up -d --build
docker compose exec api python -m scripts.seed_demo_data

# 2. Hit the smoke endpoint with Case 1 (direct VASP deposit)
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case1_suspect_001","chain":"ethereum"}'

# 3. Hit Case 5 (mixer → insufficient_evidence)
curl -X POST http://localhost:8000/api/v1/attribution/run \
  -H 'content-type: application/json' \
  -d '{"suspect_address":"0xDEMO_case5_suspect_001","chain":"ethereum"}'
```

## How to extend

- Add new transactions to `transactions.json` — keep `case: "caseN"`
  consistent.
- Add new addresses to `addresses.json`.
- Update `cases.json` if you want a new case slot (case 9, 10, …).
- Re-run the seed script.

Do **not** add real mainnet addresses or real exchange names here. The
file is intended for offline development and CI.