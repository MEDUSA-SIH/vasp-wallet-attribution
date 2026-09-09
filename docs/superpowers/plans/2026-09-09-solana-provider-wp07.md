# WP-07 Solana provider (live API integration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `SolanaProvider` stub with live Tatum gateway JSON-RPC implementation following WP-03/04/05/06 pattern.

**Architecture:** Single `SolanaProvider` class talking only to `https://solana-mainnet.gateway.tatum.io` via `httpx.AsyncClient` (injected). `get_balance` → `getBalance`; `get_transactions` → `getSignaturesForAddress` + `getTransaction` fan-out → `CanonicalTransaction`; `get_block_height` → `getBlockHeight`. Factory wires `provider_solana_enabled` flag. Native SOL MVP; SPL tokens out of scope.

**Tech Stack:** Python 3.12, `httpx.AsyncClient(timeout=10.0)`, `pytest + httpx.MockTransport`, `Decimal` with `10**9` lamport scaling.

**Spec:** `docs/work-packages.md:32` WP-07 row (`feature/solana-provider-live`, Phase 20); `docs/contracts.md §1-2` (ABC + canonical rules); live reference `api/app/providers/tron.py`, `bitcoin.py`; user gateway snippet (`getBlockHeight` via `solana-mainnet.gateway.tatum.io` + `x-api-key`).

## Global Constraints

- `chain_code = "solana"` lowercase ASCII, unique — `api/app/providers/base.py:27`.
- All methods coroutines, never block loop; `stream_transactions` cancellable via `aclose()`; `healthcheck` <5s — `docs/contracts.md:43-50`.
- `get_transactions` returns ascending timestamp; pagination caller's job beyond `limit` — `docs/contracts.md:45`.
- `CanonicalTransaction` frozen/slots; `amount` human SOL units, `fee` native SOL, `raw` JSON-serialisable — `docs/contracts.md:76-81`.
- No global state; config only via `app.config.Settings` — `docs/contracts.md:48`.
- Errors → `ProviderError` (`api/app/core/exceptions.py:13-14`), never raw `httpx`/leaked keys.
- Single WP scope; frozen contracts unbroken; `ruff check + format`, `pytest` green.

---

## File structure

| File | Responsibility |
|------|----------------|
| Modify `api/app/providers/solana.py:1-48` | Full live impl (init, headers, `_rpc_post`, 4 ABC methods + `aclose`, `_to_canonical`) |
| Modify `api/app/providers/factory.py:61-71` | Add `elif solana + provider_solana_enabled` branch + docstring WP-07 |
| Create `api/tests/unit/test_solana_provider.py` | 9 mocked tests mirroring `test_tron_provider.py` |
| Modify `docs/work-packages.md:32` | Mark WP-07 Claimed/Done (deferred, owner approval) — OUT OF SCOPE for implementers unless plan says so |
| No change `api/app/config.py:76,86`, `.env.example:59-84` | `provider_solana_enabled`, `solana_provider_url`, `blockchain_api_key` already exist |

Key RPC shapes (Tatum gateway = vanilla Solana JSON-RPC):

```json
// getBalance {"jsonrpc":"2.0","id":1,"method":"getBalance","params":["Addr"]}
// → {"result":{"value":1234567890}}  // lamports
// getSignaturesForAddress {"method":"getSignaturesForAddress","params":["Addr",{"limit":50,"commitment":"finalized"}]}
// → {"result":[{"signature":"abc","slot":280M,"blockTime":1719226761,"err":null}]}
// getTransaction {"method":"getTransaction","params":["abc",{"encoding":"json","maxSupportedTransactionVersion":0}]}
// → {"result":{"slot":280M,"blockTime":1719226761,"meta":{"err":null,"fee":5000,"preBalances":[..],"postBalances":[..]},"transaction":{"message":{"accountKeys":[..]}}}}
// getBlockHeight → {"result": 291846993}  // int, NOT 0x-hex (unlike Tron/EVM)
```

Canonical mapping decision (locked): `block_height = slot`, `block_timestamp = blockTime`, `fee = meta.fee/1e9`, `from = accountKeys[0]`, `to = first key with post>pre` (fallback: queried addr if involved else `accountKeys[1]`), `amount = max balance increase/1e9`, `success = meta.err is None`, `asset_symbol="SOL"`.

---

### Task 1: Failing test scaffold + balance/height

**Files:**
- Create: `api/tests/unit/test_solana_provider.py`
- Modify: none yet (provider still stub — tests must fail)
- Test: `api/tests/unit/test_solana_provider.py`

**Interfaces:**
- Consumes: `Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key, solana_provider_url)`, `httpx.MockTransport`
- Produces: `_make_provider()`, fixtures `ADDR/OTHER/SIG1`, mock dispatch by `method` name (contract for Task 2)

- [ ] **Step 1: Write failing tests (balance + height + factory)**

```python
"""Solana live provider tests — mocked gateway JSON-RPC (WP-07)."""
from __future__ import annotations
from decimal import Decimal
import httpx, pytest
from app.config import Settings
from app.providers.factory import build_default_provider_registry
from app.providers.solana import SolanaProvider

ADDR = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1"
OTHER = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2"

def _mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json
    body = _json.loads(request.content.decode() or "{}")
    method = body.get("method")
    if method == "getBalance":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"value": 2500000000}})
    if method == "getBlockHeight":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 291846993})
    return httpx.Response(404, json={"message": "not found"})

def _make_provider() -> SolanaProvider:
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="test-key", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example")
    return SolanaProvider(settings=settings, client=client)

@pytest.mark.asyncio
async def test_get_balance_converts_lamports() -> None:
    provider = _make_provider()
    assert await provider.get_balance(ADDR) == Decimal("2.5")
    await provider.aclose()

@pytest.mark.asyncio
async def test_get_block_height_via_gateway() -> None:
    provider = _make_provider()
    assert await provider.get_block_height() == 291846993
    await provider.aclose()

def test_factory_registers_live_solana_when_enabled() -> None:
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="test-key", solana_provider_url="https://tatum.example/")
    reg = build_default_provider_registry(settings)
    provider = reg.get("solana")
    assert isinstance(provider, SolanaProvider)
    assert provider.chain_code == "solana"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest api/tests/unit/test_solana_provider.py -v`
Expected: FAIL (`ProviderError: Provider 'solana' is not implemented yet`, factory returns stub without `_settings`).

- [ ] **Step 3: Commit scaffold (tests-only, allowed to be red on branch)**

```bash
git add api/tests/unit/test_solana_provider.py
git commit -m "test(solana): scaffold WP-07 failing tests"
```

---

### Task 2: Core provider — init, RPC helper, balance, height, healthcheck

**Files:**
- Modify: `api/app/providers/solana.py:1-48`
- Test: `api/tests/unit/test_solana_provider.py` (Task 1 tests)

**Interfaces:**
- Consumes: `Settings.blockchain_api_key/solana_provider_url`, `httpx.AsyncClient`
- Produces: `SolanaProvider(settings, client)`, `_headers()`, `_rpc_post(method, params)`, `get_balance/get_block_height/healthcheck/aclose()` — `get_transactions` still raises (Task 3 fills it)

- [ ] **Step 1: Extend tests for auth/error/healthcheck**

```python
@pytest.mark.asyncio
async def test_healthcheck_true() -> None:
    provider = _make_provider()
    assert await provider.healthcheck() is True
    await provider.aclose()

@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example")
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_balance(ADDR)
    await provider.aclose()

@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="bad-key", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_fail), base_url="https://tatum.example")
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()
```

(add `from app.core.exceptions import ProviderError` import)

- [ ] **Step 2: Run, confirm new tests fail**

Run: `pytest api/tests/unit/test_solana_provider.py -v`
Expected: FAIL (stub).

- [ ] **Step 3: Minimal implementation (copy Tron shape, Solana methods)**

```python
"""Solana live provider — Tatum gateway JSON-RPC (Phase 20, WP-07)."""
from __future__ import annotations
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
import httpx
from app.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction

_DEFAULT_GATEWAY_URL = "https://solana-mainnet.gateway.tatum.io"
_LAMPORTS_PER_SOL = Decimal(10) ** 9

class SolanaProvider(BlockchainProvider):
    """Live Solana provider backed by Tatum gateway JSON-RPC."""
    chain_code = "solana"
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._gateway_url = (self._settings.solana_provider_url or _DEFAULT_GATEWAY_URL).rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._req_id = 0
    async def aclose(self) -> None:
        await self._client.aclose()
    def _headers(self) -> dict[str, str]:
        key = self._settings.blockchain_api_key
        if not key:
            raise ProviderError("Solana provider: BLOCKCHAIN_API_KEY is not set")
        return {"accept": "application/json", "content-type": "application/json", "x-api-key": key}
    async def _rpc_post(self, method: str, params: list[Any]) -> Any:
        import asyncio
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
        for attempt in range(2):
            try:
                resp = await self._client.post(self._gateway_url, headers=self._headers(), json=payload)
            except httpx.HTTPError as exc:
                raise ProviderError("Solana provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Solana provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Solana provider error: HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ProviderError("Solana provider: bad JSON") from exc
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                msg = str(err.get("message", err) if isinstance(err, dict) else err)[:160]
                raise ProviderError(f"Solana provider error: {msg!r}")
            return data.get("result") if isinstance(data, dict) else data
        raise ProviderError("Solana provider error: rate limited")
    async def get_balance(self, address: str) -> Decimal:
        result = await self._rpc_post("getBalance", [address])
        try:
            lamports = result.get("value", 0) if isinstance(result, dict) else 0
            return Decimal(str(lamports)) / _LAMPORTS_PER_SOL
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ProviderError("Solana provider: bad balance payload") from exc
    async def get_block_height(self) -> int:
        result = await self._rpc_post("getBlockHeight", [])
        try:
            return int(str(result)) if not isinstance(result, int) else result
        except (ValueError, TypeError) as exc:
            raise ProviderError("Solana provider: bad block height") from exc
    async def healthcheck(self) -> bool:
        try:
            await self.get_block_height()
        except ProviderError:
            return False
        return True
    async def get_transactions(self, address: str, *, start_time: Any = None, end_time: Any = None, limit: int = 100) -> list[CanonicalTransaction]:
        raise ProviderError("Solana provider: get_transactions not yet implemented (Task 3)")
    async def stream_transactions(self, address: str, *, start_time: Any = None) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx
```

- [ ] **Step 4: Run**

Run: `pytest api/tests/unit/test_solana_provider.py -v`
Expected: PASS (6 tests; `get_transactions` covered in Task 3).

- [ ] **Step 5: Commit**

```bash
git add api/app/providers/solana.py api/tests/unit/test_solana_provider.py
git commit -m "feat(solana): live balance/height via gateway RPC"
```

---

### Task 3: Transaction history — sigs fan-out + canonical mapping

**Files:**
- Modify: `api/app/providers/solana.py` (replace Task 2 `get_transactions` raise with real impl + `_to_canonical`)
- Test: `api/tests/unit/test_solana_provider.py` (append)

**Interfaces:**
- Consumes: `_rpc_post()` from Task 2
- Produces: `get_transactions(address, *, start_time, end_time, limit) -> list[CanonicalTransaction]` ascending; `_to_canonical(address, sig_row, sig, detail)`.

- [ ] **Step 1: Write failing tx tests**

```python
SIG1 = "5UfDuX7M5Y2k9QwErTyUiOpAsDfGhJkLzXcVbNm123456789abcd"
TX_DETAIL = {
    "slot": 280000001,
    "blockTime": 1719226761,
    "meta": {"err": None, "fee": 5000, "preBalances": [3000000000, 1000000], "postBalances": [2000000000, 1000001000]},
    "transaction": {"message": {"accountKeys": [ADDR, OTHER]}},
}
# extend _mock_handler: if method == "getSignaturesForAddress": return {"result": [{"signature": SIG1, "slot": 280000001, "blockTime": 1719226761, "err": None}]}
# if method == "getTransaction": return {"result": TX_DETAIL}

@pytest.mark.asyncio
async def test_get_transactions_maps_sol_to_canonical() -> None:
    provider = _make_provider()
    txs = await provider.get_transactions(ADDR)
    assert len(txs) == 1
    assert txs[0].chain == "solana" and txs[0].tx_hash == SIG1
    assert txs[0].from_address == ADDR and txs[0].to_address == OTHER
    assert txs[0].amount == Decimal("1") and txs[0].asset_symbol == "SOL"
    assert txs[0].block_height == 280000001 and txs[0].success is True
    assert txs[0].raw.get("source") == "solana-rpc"
    await provider.aclose()

@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter() -> None:
    from datetime import UTC, datetime
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1719226761, tz=UTC)
    assert await provider.get_transactions(ADDR, start_time=cutoff) == []
    await provider.aclose()

@pytest.mark.asyncio
async def test_stream_transactions_yields() -> None:
    provider = _make_provider()
    seen = [t.tx_hash async for t in provider.stream_transactions(ADDR)]
    assert seen == [SIG1]
    await provider.aclose()

@pytest.mark.asyncio
async def test_rate_limit_retries_once() -> None:
    calls = {"n": 0}
    def _flaky(request: httpx.Request) -> httpx.Response:
        import json as _json
        body = _json.loads(request.content.decode() or "{}")
        if body.get("method") == "getSignaturesForAddress" and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(429, json={"message": "rate limited"})
        return _mock_handler(request)
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="test-key", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_flaky), base_url="https://tatum.example")
    provider = SolanaProvider(settings=settings, client=client)
    assert len(await provider.get_transactions(ADDR, limit=1)) == 1 and calls["n"] == 1
    await provider.aclose()
```

- [ ] **Step 2: Run, confirm fail** (`get_transactions not yet implemented`).
- [ ] **Step 3: Implement**

```python
async def get_transactions(self, address, *, start_time=None, end_time=None, limit=100) -> list[CanonicalTransaction]:
    sigs: list[dict[str, Any]] = []
    before: str | None = None
    while len(sigs) < limit:
        opt: dict[str, Any] = {"limit": min(max(limit - len(sigs), 1), 1000), "commitment": "finalized"}
        if before: opt["before"] = before
        batch = await self._rpc_post("getSignaturesForAddress", [address, opt])
        if not isinstance(batch, list) or not batch: break
        sigs.extend(r for r in batch if isinstance(r, dict) and r.get("signature"))
        before = str(batch[-1].get("signature")) if batch else None
        if len(batch) < opt["limit"]: break
    out: list[CanonicalTransaction] = []
    for row in sigs[:limit]:
        sig = str(row.get("signature"))
        detail = await self._rpc_post("getTransaction", [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}])
        if not isinstance(detail, dict): continue
        out.append(self._to_canonical(address, row, sig, detail))
    out.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))
    if start_time is not None: out = [t for t in out if t.block_timestamp is None or t.block_timestamp > start_time]
    if end_time is not None: out = [t for t in out if t.block_timestamp is None or t.block_timestamp <= end_time]
    return out[:limit]

def _to_canonical(self, address: str, sig_row: dict[str, Any], sig: str, detail: dict[str, Any]) -> CanonicalTransaction:
    meta = detail.get("meta") if isinstance(detail.get("meta"), dict) else {}
    msg = detail.get("transaction", {}).get("message", {}) if isinstance(detail.get("transaction"), dict) else {}
    keys = msg.get("accountKeys", []) if isinstance(msg, dict) else []
    keys = [str(k) for k in keys if isinstance(k, (str,))]
    pre = meta.get("preBalances", []) if isinstance(meta.get("preBalances"), list) else []
    post = meta.get("postBalances", []) if isinstance(meta.get("postBalances"), list) else []
    increase, to_addr = Decimal("0"), None
    for i, k in enumerate(keys):
        try:
            delta = Decimal(str(post[i])) - Decimal(str(pre[i])) if i < len(pre) and i < len(post) else Decimal("0")
        except (InvalidOperation, ValueError): delta = Decimal("0")
        if delta > increase: increase, to_addr = delta, k
    try: amount = increase / _LAMPORTS_PER_SOL
    except (InvalidOperation, ValueError): amount = Decimal("0")
    try: fee = Decimal(str(meta.get("fee", 0) or 0)) / _LAMPORTS_PER_SOL
    except (InvalidOperation, ValueError): fee = Decimal("0")
    from_addr = keys[0] if keys else None
    if to_addr is None:
        to_addr = address if address in keys else (keys[1] if len(keys) > 1 else None)
    bt = detail.get("blockTime", sig_row.get("blockTime"))
    try: ts = datetime.fromtimestamp(int(str(bt)), tz=UTC) if bt is not None else None
    except (ValueError, TypeError, OSError, OverflowError): ts = None
    slot = detail.get("slot", sig_row.get("slot"))
    try: bh = int(str(slot)) if slot is not None and int(str(slot)) >= 0 else None
    except (ValueError, TypeError): bh = None
    return CanonicalTransaction(chain="solana", tx_hash=sig, block_height=bh, block_timestamp=ts, from_address=(str(from_addr) if from_addr else None), to_address=(str(to_addr) if to_addr else None), asset_symbol="SOL", amount=amount, fee=fee, success=(meta.get("err") is None), raw={"source": "solana-rpc", "signature": sig_row, "detail": detail})
```

Note: `> start_time` (not `>=`) matches Tron/BNB convention; EVM-Ethereum uses `>=` — Solana follows Tron side intentionally.

- [ ] **Step 4: Run** `pytest api/tests/unit/test_solana_provider.py -v` → PASS (10 tests).
- [ ] **Step 5: Commit** `git commit -m "feat(solana): sigs fan-out + SOL canonical mapping"`.

---

### Task 4: Factory wiring + verification

**Files:**
- Modify: `api/app/providers/factory.py:39-40,61-71`
- Test: existing Task 1 factory test + `api/tests/unit/test_provider_factory.py`

**Interfaces:** Consumes `Settings.provider_solana_enabled`; produces live `SolanaProvider(settings)` in non-demo registry.

- [ ] **Step 1: Confirm failing factory test** (already written in Task 1 — run it, expect `cls()` stub without `_settings`).
- [ ] **Step 2: Implement (2 lines + docstring)**

```python
# docstring L39: live providers where enabled (WP-03 bitcoin, WP-04 ethereum, WP-05 tron, WP-06 bnb, WP-07 solana),
elif _code == "solana" and settings.provider_solana_enabled:
    registry.register(SolanaProvider(settings=settings))
```

insert between `bnb` branch and `else`, mirroring `tron.py:66-67` style.

- [ ] **Step 3: Run**

Run: `pytest api/tests/unit/test_solana_provider.py api/tests/unit/test_provider_factory.py api/tests/unit/test_providers.py -v`
Expected: PASS. Then: `ruff check api/ packages/` + `ruff format --check api/app/providers/solana.py api/app/providers/factory.py api/tests/unit/test_solana_provider.py`
- [ ] **Step 4: Manual live check (read-only, optional, never in CI)** — skip if no key; never commit keys.
- [ ] **Step 5: Commit** `git commit -m "feat(solana): wire live provider in factory"`.
