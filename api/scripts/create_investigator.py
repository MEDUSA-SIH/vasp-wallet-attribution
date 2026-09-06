"""Create an investigator from the CLI (admin bootstrap).

Run with:

    python -m scripts.create_investigator \
        --email ops@banner.gov --full-name "Ops Admin" \
        --role admin --password "$ADMIN_PASSWORD"

Idempotent: if the email already exists the script exits non-zero and
touches nothing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.schemas.auth import InvestigatorCreate  # noqa: E402
from app.services import investigator_service as svc  # noqa: E402

app = typer.Typer()


async def _run(payload: InvestigatorCreate) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with async_sessionmaker(bind=engine, expire_on_commit=False)() as session:
            inv = await svc.create_investigator(session, payload)
            await session.commit()
            print(f"created investigator id={inv.id} role={inv.role} email={inv.email}")
    finally:
        await engine.dispose()


@app.command()
def main(
    email: str = typer.Option(..., help="Investigator email"),
    full_name: str = typer.Option(..., help="Display name"),
    role: str = typer.Option("investigator", help="investigator | reviewer | admin"),
    password: str = typer.Option(..., help="Initial password (min 8 chars)"),
    agency: str = typer.Option(None, help="Agency / department"),
) -> None:
    email = email.lower()
    try:
        payload = InvestigatorCreate(
            email=email, full_name=full_name, role=role, password=password, agency=agency
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=2) from None
    try:
        asyncio.run(_run(payload))
    except svc.DuplicateEmailError:
        print(f"investigator {email} already exists; nothing to do", file=sys.stderr)
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
