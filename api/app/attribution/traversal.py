"""Stage B — Path reconstruction (Phase 10 / Phase 22).

Discovery already materialises the full path of addresses and edges on
every :class:`Candidate`. Stage B's job is to enrich each candidate
with:

- ``hop_sequence`` — the ordered list of ``(chain, address)`` pairs
  traversed from suspect to terminal.
- ``key_tx_hashes`` — the chain-specific tx hashes that constitute
  the candidate's evidence trail (used in reports downstream).
- ``path_integrity`` — a 0..1 boolean signal (1.0 = every hop has a
  real CanonicalTransaction backing it, 0.0 = nothing).

Stage B is a pure transformation; it does not consult providers.
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
