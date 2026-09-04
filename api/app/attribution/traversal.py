"""Step B — Rebuild the full path.

The search step already collects the path for each candidate. This step
wraps it in a scored container and adds helpers:

- ``hop_sequence`` — ordered list of addresses from suspect to terminal
- ``key_tx_hashes`` — transaction hashes that support the path
- ``path_integrity`` — 1 if every hop has a real transaction, else 0

This is a simple data transformation — it does not call any external service.
"""

from __future__ import annotations

from app.attribution.types import Candidate, ScoredCandidate


def reconstruct(candidates: list[Candidate]) -> list[ScoredCandidate]:
    """Wrap each :class:`Candidate` in a :class:`ScoredCandidate` shell."""
    out: list[ScoredCandidate] = []
    for cand in candidates:
        scored = ScoredCandidate(candidate=cand)
        out.append(scored)
    return out


def hop_sequence(cand: Candidate) -> list[dict[str, str]]:
    """Ordered list of ``{chain, address}`` pairs along the path."""
    chain = cand.chain
    return [{"chain": chain, "address": addr} for addr in cand.path]


def key_tx_hashes(cand: Candidate) -> list[str]:
    """Tx hashes that constitute the candidate's evidence trail."""
    return [e.tx_hash for e in cand.edges]


def path_integrity(cand: Candidate) -> float:
    """1.0 if every hop is backed by a CanonicalTransaction, else 0.0."""
    if not cand.edges:
        return 0.0
    return 1.0 if cand.hops == len(cand.edges) else 0.0


__all__ = ["reconstruct", "hop_sequence", "key_tx_hashes", "path_integrity"]
