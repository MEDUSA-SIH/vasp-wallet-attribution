# Makefile
# Convenience targets for SIH26182 VASP attribution monorepo.
# Run `make help` to list targets.

.DEFAULT_GOAL := help
.PHONY: help up down logs build restart migrate test lint format shell seed-demo clean \
        revision check install-hooks pre-commit branch work-packages

help:
	@echo "Available targets:"
	@echo "  up              - docker compose up (build + detach)"
	@echo "  down            - docker compose down"
	@echo "  logs            - tail api logs"
	@echo "  build           - docker compose build"
	@echo "  restart         - restart the api service"
	@echo "  migrate         - run Alembic upgrade head inside api container"
	@echo "  test            - run pytest inside api container"
	@echo "  lint            - run ruff check"
	@echo "  format          - run ruff format"
	@echo "  shell           - open a bash shell in the api container"
	@echo "  seed-demo       - load offline demo dataset (later stage)"
	@echo "  clean           - remove dangling docker resources"
	@echo "  install-hooks   - install pre-commit hooks (once per machine)"
	@echo "  pre-commit      - run pre-commit on all files"
	@echo "  revision m=...  - generate an alembic migration"
	@echo "  check           - run scripts/check.sh (lint + import smoke)"
	@echo "  branch NAME=... - create a feature/<NAME> branch off develop"
	@echo "  work-packages   - open docs/work-packages.md in the default editor"

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

install-hooks:
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
	else \
		pip install --user pre-commit && pre-commit install; \
	fi

pre-commit:
	pre-commit run --all-files

revision:
	@if [ -z "$(m)" ]; then \
		echo "Usage: make revision m='short description'"; \
		exit 1; \
	fi
	docker compose exec api alembic revision --autogenerate -m "$(m)"

check:
	./scripts/check.sh

branch:
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make branch NAME=short-kebab-name"; \
		exit 1; \
	fi
	git checkout develop
	git pull --ff-only origin develop || true
	git checkout -b feature/$(NAME)
	@echo "Created branch feature/$(NAME) off develop."

work-packages:
	@$${EDITOR:-less} docs/work-packages.md