"""Risk typology catalog (Phase 14)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Typology:
    """A single risk typology (e.g. mixer, peel chain, layered exchange)."""

    code: str
    label: str
    description: str


_TYPOLOGIES: tuple[Typology, ...] = (
    Typology("mixer", "Mixer / Tumbler", "Funds routed through a mixing service."),
    Typology("peel_chain", "Peel chain", "Long chain of small transfers peeling off value."),
    Typology(
        "nested_service", "Nested VASP service", "Funds routed through an inner exchange account."
    ),
    Typology("bridge_abuse", "Cross-chain bridge abuse", "Suspicious cross-chain bridge usage."),
)


def list_typologies() -> tuple[Typology, ...]:
    """Return the static typology catalog (Phase 14)."""
    return _TYPOLOGIES


__all__ = ["Typology", "list_typologies"]
