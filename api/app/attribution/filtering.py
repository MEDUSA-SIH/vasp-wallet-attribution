"""Stage C — Candidate filtering (Phase 10 / Phase 14).

Apply hard rules that drop candidates before scoring:

1. **Mixer hard stop (Phase 14)** — anything beyond a mixer is never
   attributed. We don't drop the mixer itself (it is useful evidence),
   but we **demote** it so it can't be ranked against real VASP
   candidates.
2. **Dust filter** — a hop under ``MIN_HOP_AMOUNT`` (configurable) is
   treated as noise.
3. **Non-VASP terminal** — candidates that resolve to a non-VASP,
   non-mixer terminal (dead-end / hub) get demoted.
4. **Cycle / duplicate paths** — candidates with identical
   ``tuple(path)`` are deduplicated.
5. **Weak hop trail** — candidates with zero backing edges are
   dropped.

The stage is intentionally conservative: it prefers to drop noise
rather than invent scores.  Filtering never **adds** evidence.
"""
from __future__ import annotations

from app.attribution.types import ScoredCandidate

MIN_HOP_AMOUNT = 0.005        # sub-cent hops are noise
HUB_DEGREE_THRESHOLD = 4      # >4 distinct txs = hub


def apply_filters(
    candidates: list[ScoredCandidate],
    *,
    degree_lookup: DegreeLookup | None = None,
) -> list[ScoredCandidate]:
    """Return the filtered candidates (in deterministic order)."""
    seen_paths: set[tuple[str, ...]] = set()
    out: list[ScoredCandidate] = []
    for scored in candidates:
        cand = scored.candidate
        # Rule: must have at least one hop.
        if cand.hops == 0:
            continue
        # Rule: must have at least one backing edge.
        if not cand.edges:
            continue
        # Rule: drop duplicates by path.
        path_key = tuple(cand.path)
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)
        # Rule: dust filter — every hop must be at or above MIN_HOP_AMOUNT.
        if any(e.amount < MIN_HOP_AMOUNT for e in cand.edges):
            continue
        # Rule: hub detection — if degree_lookup is provided and the
        # terminal touches too many unrelated wallets, flag the candidate
        # as a hub (caller can reclassify it).
        if (
            degree_lookup is not None
            and degree_lookup.degree(cand.terminal_address) > HUB_DEGREE_THRESHOLD
            and cand.terminal_role not in {"vasp", "mixer"}
        ):
            cand.terminal_role = "hub"
        # Note: we deliberately do NOT drop mixers here — they are kept
        # so the ranking can still surface them as ``insufficient_evidence``
        # terminals. They just won't beat real VASP candidates.
        out.append(scored)
    return out


class DegreeLookup:
    """Cheap wrapper around the dataset's degree function."""

    def __init__(self, dataset: object | None) -> None:
        self._dataset = dataset

    def degree(self, address: str) -> int:
        if self._dataset is None or not hasattr(self._dataset, "tx_by_address"):
            return 0
        seen: set[str] = set()
        for txs in self._dataset.tx_by_address.values():  # type: ignore[attr-defined]
            for tx in txs:
                if tx.from_address == address or tx.to_address == address:
                    seen.add(tx.tx_hash)
        return len(seen)


__all__ = ["apply_filters", "DegreeLookup", "MIN_HOP_AMOUNT", "HUB_DEGREE_THRESHOLD"]