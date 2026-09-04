"""Attribution service — connects the API to the engine.

The main method ``run_demo_attribution`` is used by ``POST /api/v1/attribution/run``.
It runs the attribution engine and converts the result into the API response format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.attribution.engine import AttributionEngine, AttributionResult
from app.attribution.filtering import DegreeLookup
from app.providers.base import ProviderRegistry

DEFAULT_MAX_HOPS = 5


@dataclass(slots=True)
class AttributionRunResult:
    """Wire-format result returned by the smoke endpoint."""

    run_id: UUID
    case_id: UUID | None
    suspect_address: str
    chain: str
    outcome: str
    insufficient_evidence: bool
    demo_mode: bool
    candidates: list[dict[str, Any]]
    explanations: dict[str, str]
    hops_used: int
    started_at: datetime
    finished_at: datetime | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["run_id"] = str(self.run_id)
        if self.case_id is not None:
            d["case_id"] = str(self.case_id)
        d["started_at"] = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        return d


class AttributionService:
    """Glue between the API and the :class:`AttributionEngine`."""

    def __init__(self, engine: AttributionEngine | None = None) -> None:
        self.engine = engine or AttributionEngine()

    async def run_demo_attribution(
        self,
        suspect_address: str,
        *,
        chain: str = "ethereum",
        registry: ProviderRegistry,
        case_id: UUID | None = None,
        max_hops: int = DEFAULT_MAX_HOPS,
    ) -> AttributionRunResult:
        """Run the engine against the demo providers and shape the response."""
        run_id = uuid4()
        # A cheap degree lookup against the demo dataset, when available.
        degree_lookup = _build_degree_lookup(registry, chain)
        engine = AttributionEngine(max_hops=max_hops)
        started = datetime.utcnow()
        result: AttributionResult = await engine.run(
            suspect_address,
            chain=chain,
            registry=registry,
            case_id=case_id,
            degree_lookup=degree_lookup,
        )
        finished = datetime.utcnow()

        candidates = [c.as_dict() for c in result.candidates]
        hops_used = max((c.candidate.hops for c in result.candidates), default=0)

        return AttributionRunResult(
            run_id=run_id,
            case_id=case_id,
            suspect_address=suspect_address,
            chain=chain,
            outcome=result.outcome,
            insufficient_evidence=result.insufficient_evidence,
            demo_mode=True,
            candidates=candidates,
            explanations=result.explanations,
            hops_used=hops_used,
            started_at=started,
            finished_at=finished,
            notes=[
                "Attribution engine with 8 stages is implemented — see docs/development.md.",
                "Scoring is a simple, explainable first version; future improvements will refine the formulas.",
            ],
        )


def _build_degree_lookup(registry: ProviderRegistry, chain: str) -> DegreeLookup | None:
    """Return a :class:`DegreeLookup` over the demo dataset if available."""
    try:
        provider = registry.get(chain)
    except KeyError:
        return None
    dataset = getattr(provider, "_dataset", None)
    if dataset is None:
        return None
    return DegreeLookup(dataset)


__all__ = ["AttributionService", "AttributionRunResult"]
