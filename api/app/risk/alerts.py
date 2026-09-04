"""Risk alert checks."""

from __future__ import annotations

from typing import Any


async def evaluate_alerts(wallet_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the alert rule set against a wallet's metrics.

    Returns an empty list for now; a later stage will check the metrics
    against the typology catalog and produce alert records.
    """
    return []


__all__ = ["evaluate_alerts"]
