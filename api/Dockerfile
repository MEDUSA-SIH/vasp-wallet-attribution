# syntax=docker/dockerfile:1.7
# api/Dockerfile
# Multi-stage production-leaning image for the SIH26182 FastAPI service.

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.0

# ---------- Stage 1: build dependencies with uv ---------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -fsSL "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /build

# Copy dependency manifest first for better layer caching
COPY pyproject.toml ./

# uv sync resolves deps from pyproject. We install the package + dev extras into a venv
RUN uv venv /opt/venv \
 && uv pip install --python /opt/venv/bin/python ".[dev]" || \
    (echo "Dev install failed; retrying without dev" && uv pip install --python /opt/venv/bin/python ".")

ENV PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv

# ---------- Stage 2: runtime --------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv \
    APP_HOME=/home/sih26182/app

RUN apt-get update \
 && apt-get install -y --no-install-recommends tini curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 sih26182 \
 && useradd  --system --uid 1000 --gid sih26182 --create-home --shell /bin/bash sih26182

WORKDIR ${APP_HOME}

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=sih26182:sih26182 . ${APP_HOME}

USER sih26182

EXPOSE 8000

# Healthcheck uses /api/v1/health defined in app/api/v1/health.py
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=10 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
# Default command: uvicorn. docker-compose can override this for dev (--reload).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]