# Convenience targets for SIH26182 VASP attribution monorepo.
# Run `make help` to list targets.

.DEFAULT_GOAL := help
.PHONY: help up down logs build restart migrate test lint format shell seed-demo clean

help:
	@echo "Available targets:"
	@echo "  up            - docker compose up (build + detach)"
	@echo "  down          - docker compose down"
	@echo "  logs          - tail api logs"
	@echo "  build         - docker compose build"
	@echo "  restart       - restart the api service"
	@echo "  migrate       - run Alembic upgrade head inside api container"
	@echo "  test          - run pytest inside api container"
	@echo "  lint          - run ruff check"
	@echo "  format        - run ruff format"
	@echo "  shell         - open a bash shell in the api container"
	@echo "  seed-demo     - load offline demo dataset (synthetic data)"
	@echo "  clean         - remove dangling docker resources"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

build:
	docker compose build

restart:
	docker compose restart api

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest

lint:
	cd api && ruff check .

format:
	cd api && ruff format .

shell:
	docker compose exec api bash

seed-demo:
	docker compose exec api python -m scripts.seed_demo_data

clean:
	docker system prune -f