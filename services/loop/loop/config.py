"""Load model IDs and runtime settings. Model IDs are never inlined at call sites (P-6)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_PATH = REPO_ROOT / "config" / "models.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "var"


class ModelSpec(BaseModel):
    id: str
    lifecycle_tier: str
    sampling_supported: bool = True
    temperature: float | None = None
    top_p: float | None = None
    retires: str | None = None
    architecturally_optional: bool = False
    sampling_silently_ignored: list[str] = Field(default_factory=list)


class ModelsFile(BaseModel):
    default_reasoning: ModelSpec
    voice: ModelSpec
    embeddings: ModelSpec
    memory_generation: ModelSpec
    opt_in_newer: list[ModelSpec]
    forbidden: list[str]
    region: str
    project_env: str


@lru_cache(maxsize=1)
def load_models(path: Path | None = None) -> ModelsFile:
    raw = yaml.safe_load((path or MODELS_PATH).read_text())
    return ModelsFile.model_validate(raw)


def default_model_id() -> str:
    return load_models().default_reasoning.id


def generate_content_config_for(model_id: str) -> dict[str, Any] | None:
    """Return sampling kwargs only when the model honours them (P-6b)."""
    models = load_models()
    specs = [models.default_reasoning, models.voice, models.embeddings, models.memory_generation]
    specs.extend(models.opt_in_newer)
    match = next((s for s in specs if s.id == model_id), None)
    if match is None or not match.sampling_supported:
        return None
    cfg: dict[str, Any] = {}
    if match.temperature is not None:
        cfg["temperature"] = match.temperature
    if match.top_p is not None:
        cfg["top_p"] = match.top_p
    return cfg or None


def silently_ignored_sampling_models() -> set[str]:
    models = load_models()
    return {s.id for s in models.opt_in_newer if not s.sampling_supported}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOOP_", extra="ignore")

    project: str = Field(default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
    region: str = "us-central1"
    data_dir: Path = DEFAULT_DATA_DIR
    warehouse_dir: Path | None = None
    host: str = "0.0.0.0"
    port: int = 8080
    console_origin: str = "http://127.0.0.1:3000"
    model_armor_fail_closed: bool = True
    block_on_screening_failure: bool = True
    contact_frequency_cap_per_user: int = 1
    token_budget_per_investigation: int = 200_000
    verification_days: int = 3

    def warehouse_path(self) -> Path:
        return self.warehouse_dir or (self.data_dir / "warehouse")

    def db_path(self) -> Path:
        return self.data_dir / "loop.db"


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
