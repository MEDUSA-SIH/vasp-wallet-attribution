"""Create the database if it does not exist.

Used by integration tests / first-run bootstrapping. Production deploys
will rely on the orchestrated Postgres container instead.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from app.config import get_settings  # noqa: E402


async def _ensure_database() -> None:
    s = get_settings()
    conn = await asyncpg.connect(
        host=s.postgres_host,
        port=s.postgres_port,
        user=s.postgres_user,
        password=s.postgres_password,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", s.postgres_db)
        if not exists:
            # Database names can't be parameters; rely on settings injection.
            await conn.execute(f'CREATE DATABASE "{s.postgres_db}"')
            print(f"created database {s.postgres_db}")
        else:
            print(f"database {s.postgres_db} already exists")
    finally:
        await conn.close()


def main() -> None:
    asyncio.run(_ensure_database())


if __name__ == "__main__":
    main()
