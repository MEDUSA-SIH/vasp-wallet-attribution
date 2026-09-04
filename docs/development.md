# SIH26182 – Development guide

## Prerequisites

- Python 3.12
- Docker + Docker Compose
- (optional) `uv` for fast Python dependency installs
  https://github.com/astral-sh/uv

## First-time setup

```bash
cp .env.example .env
docker compose up -d --build
make migrate
curl http://localhost:8000/api/v1/health
```

The `make migrate` target applies Alembic migrations to the Postgres
container.

## Day-to-day commands

| Task                          | Command                                    |
|-------------------------------|--------------------------------------------|
| Bring stack up                | `make up`                                  |
| Tail api logs                 | `make logs`                                |
| Open api shell                | `make shell`                               |
| Run tests                     | `make test`                                |
| Lint                          | `make lint`                                |
| Apply migrations              | `make migrate`                             |
| Seed demo data (later stage)  | `make seed-demo`                           |
| Tear down stack               | `make down`                                |

## Local development without Docker

```bash
cd api
uv venv
uv pip install -e ".[dev]"
cp ../.env.example .env  # edit if needed
uvicorn app.main:app --reload
```

Make sure you have a Postgres + Redis available (locally or remote) and
that `POSTGRES_HOST` / `REDIS_HOST` in `.env` point at them.

## Linting & type-checking

- `ruff check .` runs the linter.
- `ruff format .` auto-formats.
- `mypy api/app` runs static type checks (currently relaxed to
  `ignore_missing_imports = true`).

## Running a single test

```bash
docker compose exec api pytest tests/unit -k test_health
```

## Adding a new model

1. Create `api/app/db/models/<name>.py` extending `BaseModel` and any of
   the mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`).
2. Re-export it from `api/app/db/models/__init__.py`.
3. Generate an Alembic migration:

   ```bash
   docker compose exec api alembic revision --autogenerate -m "add foo"
   docker compose exec api alembic upgrade head
   ```

## Adding a new provider

1. Create `api/app/providers/<chain>.py` extending `BlockchainProvider`.
2. Set `chain_code`.
3. Register it inside `app/main.py` `lifespan()` (later stage) using the
   `ProviderRegistry`.

## Folder conventions

- **Absolute imports inside `api`** – always `from app.xxx import …`.
- **Phase references** – every public class/function must have a
  docstring referencing the relevant spec phase.
- **No secrets in source** – environment variables only.
- **DEMO_MODE first** – new features must respect the offline demo
  pathway (see `app/providers/demo.py`).