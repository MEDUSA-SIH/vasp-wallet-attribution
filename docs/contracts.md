# SIH26182 – Public Interface Contracts

This document **freezes** the public interfaces that neighbouring teams
will code against. Anything listed below is stable for the current
minor version. Breaking changes require a `BREAKING CHANGE:` footer in
the commit AND a heads-up in `#dev`.

> **Versioning rule:**
> - Adding optional parameters / methods = minor version bump (`0.1.x → 0.2.0`).
> - Removing or renaming = major bump (`0.x.y → 1.0.0`) AND migration notes.

---

## 1. `app.providers.base.BlockchainProvider`

Phase 20.3 — every chain-specific provider MUST subclass this ABC.

```python
class BlockchainProvider(ABC):
    chain_code: str   # e.g. "bitcoin"

    async def get_balance(self, address: str) -> Decimal: ...
    async def get_transactions(
        self,
        address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]: ...
    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: datetime | None = None,
    ) -> AsyncIterator[CanonicalTransaction]: ...
    async def get_block_height(self) -> int: ...
    async def healthcheck(self) -> bool: ...
```

**Contract:**

- All methods are coroutines; never block the event loop.
- `chain_code` is lowercase ASCII and unique across registered providers.
- `get_transactions` returns canonical transactions in **ascending
  timestamp** order. Pagination beyond `limit` is the caller's job.
- `stream_transactions` MUST be safe to cancel via `aclose()`.
- `healthcheck` MUST return within 5 s under normal conditions.
- Implementations MUST be safe to instantiate multiple times; they hold
  no global state. Configuration goes through `app.config.Settings`.

---

## 2. `app.providers.canonical.CanonicalTransaction`

Phase 9 — chain-agnostic tx shape consumed by every downstream layer.

```python
@dataclass(slots=True, frozen=True)
class CanonicalTransaction:
    chain: str                    # one of ChainCode values
    tx_hash: str                  # provider-side unique
    block_height: int | None
    block_timestamp: datetime | None
    from_address: str | None
    to_address: str | None
    asset_symbol: str             # "ETH", "USDT", …
    amount: Decimal               # token units, not base units
    fee: Decimal                  # native-asset fee
    success: bool = True
    raw: dict[str, Any] = {}      # original payload, opaque to us
```

**Contract:**

- `amount` is **always** in human (post-decimal) units. Callers must NOT
  apply additional scaling.
- `fee` is always denominated in the chain's native asset.
- `raw` is opaque — schema is provider-specific but MUST be JSON
  serialisable.
- The dataclass is `slots=True, frozen=True`; do NOT mutate instances.

---

## 3. `app.attribution.engine.AttributionEngine`

Phase 10 — orchestrator for the eight-stage pipeline.

```python
class AttributionEngine:
    def __init__(self, *, max_hops: int = 5, per_chain_budget: int = 3) -> None: ...
    async def run(self, case_id: UUID, seed_addresses: list[str]) -> AttributionResult: ...

@dataclass(slots=True)
class AttributionResult:
    case_id: UUID
    rankings: list[Any]
    explanations: dict[str, Any]
```

**Contract:**

- `run` is the only public entry point. The eight stages
  (`discovery → traversal → filtering → evidence → scoring → ranking →
  explainability`) are private sub-modules and may change without
  notice — consumers MUST NOT import them directly.
- `max_hops` and `per_chain_budget` clamp the resource budget. Engines
  MUST raise `AttributionError` when the budget is exceeded.
- `AttributionResult` is **stable** for `0.1.x`. `rankings` is a list of
  `AttributionRankingEntry`-shaped dicts (see
  `app.schemas.attribution.AttributionRankingEntry`).

---

## 4. `app.graph.store.GraphStore`

Phase 6 / Phase 11 — multi-chain in-process graph store.

```python
class GraphStore:
    @property
    def raw(self) -> nx.DiGraph: ...

    def add_node(self, node: GraphNode) -> None: ...
    def add_edge(self, edge: GraphEdge) -> None: ...
    def get_outgoing(self, node_id: str) -> list[tuple[str, dict[str, Any]]]: ...
    def get_incoming(self, node_id: str) -> list[tuple[str, dict[str, Any]]]: ...
    def neighbors_within(self, node_id: str, hops: int) -> set[str]: ...
```

**Contract:**

- `add_node` is idempotent: re-adding the same id with identical
  attributes is a no-op; re-adding with **different** attributes updates
  them in place.
- Node and edge ids are **strings** with a prefix (`wallet:`, `cluster:`,
  `vasp:`, …). The prefix list is defined by `NodeKind` and `EdgeKind`
  and is part of the contract.
- `neighbors_within` counts undirected hops; it ignores edge direction.
- The store is **process-local** today (NetworkX). A future swap to
  Neo4j will keep this interface stable.

---

## 5. `app.sahyog.gateway.SahyogGateway`

Phase 7 — outbound adapter to the SAHYOG inter-agency network.

```python
class SahyogGateway(ABC):
    async def fetch_case(self, external_id: str) -> SahyogCase: ...
    async def send_message(self, message: SahyogMessage) -> SahyogReceipt: ...
```

**Contract:**

- `fetch_case` MUST be safe to retry; the same `external_id` returns
  the same `SahyogCase.id`.
- `send_message` MUST be at-least-once: a transient network failure
  MAY be retried by the caller; the gateway returns the same
  `SahyogReceipt.message_id` for retries of the same `SahyogMessage`.
- A `StubSahyogGateway` ships in-tree for local dev; do NOT swap in a
  real HTTP gateway without enabling `SAHYOG_ENABLED=true`.

---

## 6. `app.config.Settings`

Phase 25 — central configuration object.

**Contract:**

- All settings come from environment variables (or `.env` in dev).
  Missing required values use documented defaults — `DEMO_MODE` defaults
  to `true`.
- Computed fields (`database_url`, `database_url_sync`, `redis_url`,
  `cors_allow_origins_list`) MUST be treated as opaque strings; do not
  parse them.
- `get_settings()` is `lru_cache`d; tests use `reset_settings_cache()`
  to re-read the environment.

---

## 7. `app.api.v1` routers

Each router exposes a stable URL surface under `/api/v1`:

| Method | Path                              | Phase |
|------|------------------------------------|-------|
| GET   | `/api/v1/health`                   | 25    |
| GET/POST | `/api/v1/cases`                 | 12    |
| GET   | `/api/v1/cases/{case_id}`          | 12    |
| GET/POST | `/api/v1/wallets`               | 11    |
| GET   | `/api/v1/wallets/{wallet_id}`      | 11    |
| POST  | `/api/v1/attribution/run`          | 10    |
| POST  | `/api/v1/reports/generate`         | 17    |
| GET   | `/api/v1/admin/settings`           | 25    |

**Contract:**

- Adding a new path is fine (minor bump).
- Removing a path or changing its semantics = major bump + migration
  notes.

---

## 8. SQLAlchemy ORM models (Phase 8)

Tables registered in `app.db.models.*` are stable:

```
investigators, cases, chains, wallets, tokens, blocks, transactions,
vasps, clusters, cluster_wallets, attributions, risks, investigations,
reports, api_requests, audit_events
```

**Contract:**

- Column **names** are frozen (snake_case).
- Adding columns is allowed (minor bump).
- Renaming or dropping columns requires a migration AND a heads-up.

---

## 9. Alembic migration policy

- `0001_initial.py` declares the schema baseline.
- New migrations are checked in under `api/alembic/versions/` with
  filenames `NNNN_<short>.py`.
- Migrations MUST be reversible (both `upgrade` and `downgrade`
  populated).

---

## 10. Cross-package shared types (`packages.common`)

Stable exports:

```python
from common.types import ChainCode, ConfidenceWeights, InvestigationSeed
```

These mirror the `Settings` enum / tuple values and MUST stay in sync.

---

## How to evolve this document

When you intentionally break one of these contracts:

1. Bump the version in `pyproject.toml` (root + api).
2. Add a `BREAKING CHANGE:` footer to the commit message.
3. Update this document and link the commit SHA at the bottom.
4. Post in `#dev` with the migration steps.

Breaking changes (record the SHA when you ship one):

- _none yet_.