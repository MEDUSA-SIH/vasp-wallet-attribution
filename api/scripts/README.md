# api/scripts

Local scripts that run inside the api container.

- `seed_demo_data.py` – load the offline synthetic dataset (Phase 21/22).
- `create_db.py`     – create the database (used by integration tests).

Run via `make seed-demo` or `docker compose exec api python -m scripts.seed_demo_data`.
"""