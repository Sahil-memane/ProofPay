"""
ProofPay Core Configuration.
Reads settings from environment variables (or a .env file via python-dotenv).
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_base_url: str = Field(default="http://localhost:8000")
    demo_mode: bool = Field(default=False)
    simulator_enabled: bool = Field(default=False)
    internal_tick_token: str = Field(default="dev-tick-token")
    policy_signing_key: str = Field(default="dev-signing-key")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://proofpay:proofpay@localhost:5432/proofpay"
    )
    database_url_sync: str = Field(
        default="postgresql://proofpay:proofpay@localhost:5432/proofpay"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_async_url(cls, v: str) -> str:
        """
        Render injects a plain postgresql:// connection string.
        SQLAlchemy asyncpg driver requires postgresql+asyncpg://.
        """
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgres://"):
            # Some older Render/Heroku format
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def coerce_sync_url(cls, v: str) -> str:
        """
        Alembic / sync engine must use psycopg2 explicitly.
        SQLAlchemy >= 2.0 with plain postgresql:// tries psycopg (v3) first,
        which is not installed — force postgresql+psycopg2:// always.
        """
        if not v:
            return v
        # Strip any existing driver prefix to get a bare host/path
        for prefix in (
            "postgresql+asyncpg://",
            "postgresql+psycopg2://",
            "postgresql://",
            "postgres://",
        ):
            if v.startswith(prefix):
                v = "postgresql+psycopg2://" + v[len(prefix):]
                break
        return v

    # ── PayPal ────────────────────────────────────────────────────────────────
    paypal_mode: str = Field(default="sandbox")
    paypal_base_url: str = Field(default="https://api-m.sandbox.paypal.com")
    paypal_client_id: str = Field(default="")
    paypal_client_secret: str = Field(default="")
    paypal_webhook_id: str = Field(default="")
    # "rest" | "mcp" | "fake"
    paypal_exec_mode: str = Field(default="fake")

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai")
    llm_api_key: str = Field(default="")
    llm_model_cheap: str = Field(default="gpt-4o-mini")
    llm_model_qa: str = Field(default="gpt-4o")
    llm_daily_cap: int = Field(default=100)

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: str = Field(default="")

    # ── Email ─────────────────────────────────────────────────────────────────
    email_mode: str = Field(default="outbox")
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")

    # ── Frontend ──────────────────────────────────────────────────────────────
    next_public_api_base: str = Field(default="http://localhost:8000")
    next_public_paypal_client_id: str = Field(default="")
    aggrid_license_key: str = Field(default="")

    @field_validator("paypal_exec_mode")
    @classmethod
    def validate_exec_mode(cls, v: str) -> str:
        allowed = {"rest", "mcp", "fake"}
        if v not in allowed:
            raise ValueError(f"paypal_exec_mode must be one of {allowed}")
        return v

    @property
    def is_fake_paypal(self) -> bool:
        return self.paypal_exec_mode == "fake"

    @property
    def paypal_credentials_present(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton for convenience
settings = get_settings()
