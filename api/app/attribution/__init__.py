"""Attribution engine (Phase 10).

Stages:
    A. Discovery        – app.attribution.discovery
    B. Traversal        – app.attribution.traversal
    C. Filtering        – app.attribution.filtering
    D. Evidence         – app.attribution.evidence
    E. Proximity scoring– app.attribution.scoring
    F. Confidence       – app.attribution.scoring
    G. Ranking          – app.attribution.ranking
    H. Explainability   – app.attribution.explainability
"""
from app.attribution.discovery import run_discovery
from app.attribution.engine import AttributionEngine, run_attribution
from app.attribution.evidence import collect_evidence
from app.attribution.explainability import explain
from app.attribution.filtering import apply_filters
from app.attribution.ranking import rank
from app.attribution.scoring import compute_confidence, compute_proximity
from app.attribution.traversal import traverse

__all__ = [
    "AttributionEngine",
    "run_attribution",
    "run_discovery",
    "traverse",
    "apply_filters",
    "collect_evidence",
    "compute_proximity",
    "compute_confidence",
    "rank",
    "explain",
]