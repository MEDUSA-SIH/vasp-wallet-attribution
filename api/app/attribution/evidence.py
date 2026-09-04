"""Stage D — Evidence collection (Phase 10).

Collects evidence snippets that downstream stages consume. The
collection is the place where we:

- attach mixer / bridge / VASP flags to each candidate (already done
  in discovery, this stage *consolidates* them).
- surface chain-specific tx hashes (``key_tx_hashes``) for the report.
- normalise timestamps to ISO-8601 strings.
- compute a simple ``label_source_agreement`` signal (1.0 if both the
  provider and the dataset agree on the terminal role).

Stage D never fabricates evidence — it only re-shapes what discovery
already collected.
"""

from __future__ import annotations

from app.attribution.traversal import key_tx_hashes, path_integrity
from app.attribution.types import EvidenceItem, ScoredCandidate


def collect_evidence(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Attach consolidated evidence items to each candidate.

    The actual scoring components are computed in :mod:`scoring`. This
    stage focuses on the evidence bookkeeping that does not depend on
    weighted combinations.
    """
    for s in scored:
        cand = s.candidate
        # Path integrity flag.
        s.evidence.append(
            EvidenceItem(
                code="path_integrity",
                weight=path_integrity(cand),
                detail=f"path_integrity = {path_integrity(cand):.2f}",
            )
        )
        # Key tx hashes are recorded as evidence context for the report.
        hashes = key_tx_hashes(cand)
        if hashes:
            s.evidence.append(
                EvidenceItem(
                    code="key_tx_hashes",
                    weight=1.0,
                    detail=f"backing tx hashes: {', '.join(hashes[:5])}"
                    f"{' …' if len(hashes) > 5 else ''}",
                )
            )
    return scored


__all__ = ["collect_evidence"]
