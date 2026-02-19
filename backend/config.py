"""Configuration loader for the PostgreSQL Observability Agent."""

from __future__ import annotations

import os
import pathlib
from functools import lru_cache
from typing import List, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Settings from environment
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    prometheus_url: str = "http://localhost:9090"
    victoria_metrics_url: str = "http://localhost:8428"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    llm_provider: str = "litellm"   # "openai" | "anthropic" | "litellm"
    
    # LiteLLM
    litellm_url: str = "http://localhost:4000"
    litellm_model: str = "gpt-4o"
    litellm_api_key: str = "sk-1234"

    # Legacy (optional fallback)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = ""  # Deprecated in favor of provider-specific model fields

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# Database list from YAML
# ---------------------------------------------------------------------------

class DatabaseEntry(BaseModel):
    name: str
    job: Optional[str] = None


def load_databases() -> List[DatabaseEntry]:
    """Load the database list from databases.yaml."""
    yaml_path = pathlib.Path(__file__).parent / "databases.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [DatabaseEntry(**db) for db in data.get("databases", [])]


@lru_cache()
def get_databases() -> tuple[DatabaseEntry, ...]:
    """Cached database list (as tuple for hashability)."""
    return tuple(load_databases())
