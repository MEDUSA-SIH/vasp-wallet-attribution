"""Seed the offline demo dataset.

Run with:

    python -m scripts.seed_demo_data
    # or, inside the api container:
    make seed-demo

The script:

1. Loads ``data/synthetic/*.json`` into a :class:`DemoDataset`.
2. Registers the dataset with the shared :class:`DemoBlockchainProvider`
   singleton so any later call to
   :func:`build_default_provider_registry` returns providers that serve
   the synthetic data.
3. Optionally upserts VASP + address rows in the relational store
   (Postgres). The DB step is **best-effort**: if the database is
   unreachable, the in-memory seed still succeeds and the operator
   sees a warning. This keeps CI usable without a Postgres container.

The script is idempotent — running it twice produces the same end
state. It does not mutate the JSON fixtures on disk.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make `app` importable when run as `python -m scripts.seed_demo_data`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.providers.demo import (  # noqa: E402
    DEFAULT_DATASET_DIR,
    DemoBlockchainProvider,
    DemoDataset,
    reset_shared_dataset,
)
from app.providers.factory import build_default_provider_registry  # noqa: E402


async def _seed_database_if_possible(dataset: DemoDataset, log) -> int:
    """Upsert VASPs into Postgres. Return the number of rows written.

    Best-effort: any failure logs a warning and returns 0.
    """
    settings = get_settings()
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.ext.asyncio import create_async_engine

        from app.db.base import BaseModel  # noqa: F401  (register models)
        from app.db.models.vasp import VASP  # noqa: E402

        engine = create_async_engine(settings.database_url, future=True)
        rows: list[dict] = []
        for v in dataset.vasps.values():
            rows.append(
                {
                    "id": None,  # server default UUID
                    "name": v["name"],
                    "country": v.get("country"),
                    "regulator": v.get("regulator"),
                    "is_indian": bool(v.get("is_indian", False)),
                }
            )
        if not rows:
            await engine.dispose()
            return 0
        async with engine.begin() as conn:
            stmt = pg_insert(VASP).values(rows).on_conflict_do_nothing()
            await conn.execute(stmt)
        await engine.dispose()
        return len(rows)
    except Exception as exc:  # noqa: BLE001 – best-effort, log everything
        log.warning("seed_demo_data.db_skipped", error=str(exc))
        return 0


async def main() -> None:
    settings = get_settings()
    configure_logging()
    log = get_logger("seed_demo_data")

    log.info("seed_demo_data.start", demo_mode=settings.demo_mode)
    dataset = DemoDataset.load(DEFAULT_DATASET_DIR)
    log.info(
        "seed_demo_data.loaded",
        cases=len(dataset.cases),
        addresses=len(dataset.addresses),
        transactions=len(dataset.transactions),
        vasps=len(dataset.vasps),
        bridges=len(dataset.bridges),
        mixers=len(dataset.mixers),
    )

    # Force the shared dataset singleton to use the freshly-loaded one.
    reset_shared_dataset()
    DemoBlockchainProvider.get_shared_dataset  # noqa: B018 – touch
    # The provider lazily loads the singleton on first instantiation; we
    # also re-register to ensure the registry reflects the loaded state.
    registry = build_default_provider_registry(settings)
    log.info("seed_demo_data.registry_ready", chains=registry.available())

    # Optional DB upsert.
    rows = await _seed_database_if_possible(dataset, log)
    if rows:
        log.info("seed_demo_data.db_upserted", vasp_rows=rows)
    else:
        log.info("seed_demo_data.db_skipped_or_empty")

    log.info("seed_demo_data.done")


if __name__ == "__main__":
    asyncio.run(main())
