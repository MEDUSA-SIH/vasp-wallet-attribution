"""Stage G — Ranking (Phase 10 / Phase 3.3).

Sort by ``proximity_rank`` ASCENDING (lower = closer). Show
``confidence_score`` alongside but **never blend them into a single
final score** for ordering.

Special outcomes:

- If no candidate has a VASP terminal → outcome is
  ``insufficient_evidence``.
- If only hub / dead-end terminals remain → ``false_candidate_filtered``
  (when there's a hub) or ``insufficient_evidence`` (when dead-ends
  only).
- Multiple VASP candidates → ``ranked_multi_candidate``.
- Exactly one VASP candidate → ``single_candidate``.
"""

from __future__ import annotations

from app.attribution.types import ScoredCandidate


def rank(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Return candidates sorted by proximity_rank, then by tier, then by hops."""
    # Primary key: proximity_rank ascending (lower = closer).
    # Secondary key: evidence tier ascending (Tier 1 < Tier 4).
    # Tertiary key: hops ascending (shorter first).
    # Final tie-break: terminal address for determinism.
    tier_priority = {1: 0, 2: 1, 3: 2, 4: 3, 99: 4}
    return sorted(
        scored,
        key=lambda s: (
            s.proximity_rank,
            tier_priority.get(int(s.evidence_tier), 99),
            s.candidate.hops,
            s.candidate.terminal_address,
        ),
    )


def classify_outcome(scored: list[ScoredCandidate]) -> tuple[str, bool]:
    """Map the ranked candidate set to a top-level outcome.

    Returns ``(outcome, insufficient_evidence)``.

    Outcome semantics:

    - ``single_candidate`` — exactly one VASP candidate.
    - ``ranked_multi_candidate`` — multiple VASP candidates.
    - ``false_candidate_filtered`` — only hub / non-VASP terminals
      with high-degree signals.
    - ``insufficient_evidence`` — no credible VASP terminal, or only
      mixer / dead-end terminals.
    """
    if not scored:
        return "insufficient_evidence", True

    vasp_candidates = [s for s in scored if s.candidate.terminal_role == "vasp"]
    mixer_candidates = [s for s in scored if s.candidate.hits_mixer]
    hub_candidates = [s for s in scored if s.candidate.terminal_role == "hub"]
    dead_end_candidates = [s for s in scored if s.candidate.terminal_role == "dead_end"]

    if vasp_candidates:
        if len(vasp_candidates) == 1:
            return "single_candidate", False
        return "ranked_multi_candidate", False
    if mixer_candidates:
        # Phase 14 hard rule: mixer = insufficient_evidence.
        return "insufficient_evidence", True
    if hub_candidates and not dead_end_candidates:
        return "false_candidate_filtered", False
    # Anything else (dead-ends only, or mixed noise).
    return "insufficient_evidence", True


__all__ = ["rank", "classify_outcome"]
