"""Application configuration via pydantic-settings (Phase 25)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings.

    All values are loaded from environment variables (or `.env` in dev).
    Phase 25 locks pydantic-settings as the source of truth.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- General -------------------------------------------------------------
    app_name: str = "sih26182-vasp-attribution"
    app_version: str = "0.1.0"
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"
    demo_mode: bool = True  # Phase 21/22 offline mode toggle

    # ---- API -----------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_allow_origins: str = "*"

    # ---- Security ------------------------------------------------------------
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # ---- Database ------------------------------------------------------------
    postgres_user: str = "sih26182"
    postgres_password: str = "sih26182"
    postgres_db: str = "sih26182"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ---- Redis ---------------------------------------------------------------
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # ---- Attribution engine (Phase 10) --------------------------------------
    attribution_max_hops: int = 5
    attribution_per_chain_budget: int = 3
    confidence_weight_proximity: float = 0.30
    confidence_weight_typology: float = 0.20
    confidence_weight_temporal: float = 0.15
    confidence_weight_behavioral: float = 0.20
    confidence_weight_clustering: float = 0.15
    confidence_min_threshold: float = 0.35

    # ---- Provider toggles (Phase 20) -----------------------------------------
    provider_bitcoin_enabled: bool = False
    provider_ethereum_enabled: bool = False
    provider_tron_enabled: bool = False
    provider_bnb_enabled: bool = False
    provider_solana_enabled: bool = False
    provider_polygon_enabled: bool = False
    provider_demo_enabled: bool = True

    blockchain_api_key: str = ""
    ethereum_provider_url: str = ""
    bitcoin_provider_url: str = ""
    tron_provider_url: str = ""
    bnb_provider_url: str = ""
    solana_provider_url: str = ""
    polygon_provider_url: str = ""

    # ---- SAHYOG (Phase 7) ----------------------------------------------------
    sahyog_base_url: str = ""
    sahyog_api_key: str = ""
    sahyog_enabled: bool = False

    # ---- Observability -------------------------------------------------------
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""

    # ---- Feature flags ----------------------------------------------------
    feature_cross_chain_bridges: bool = True
    feature_risk_typologies: bool = True
    feature_demo_data_seed: bool = False

    # ---- Computed ------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        # Alembic prefers a synchronous driver.
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (Phase 25 dependency helper)."""
    return Settings()


def reset_settings_cache() -> None:
    """For tests only – clears the LRU cache so env reloads take effect."""
    get_settings.cache_clear()


__all__ = ["Settings", "get_settings", "reset_settings_cache"]
