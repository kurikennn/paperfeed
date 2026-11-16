"""Load and validate config.yaml and persona.md."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent

SourceName = Literal["arxiv", "biorxiv", "medrxiv", "pubmed", "semanticscholar"]


class FieldConfig(BaseModel):
    name: str
    count: int = Field(ge=0, default=2)
    lookback_days: int = Field(ge=1, default=7)
    sources: list[SourceName] = ["arxiv"]
    categories: list[str] = []
    queries: list[str] = []
    fields_of_study: list[str] = []

    @field_validator("queries")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        return [q.strip() for q in v if q and q.strip()]


class ClaudeConfig(BaseModel):
    model: str = "claude-opus-5-5"
    select_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"
    summarize_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    fallbacks: bool = True


class Config(BaseModel):
    total: int = Field(ge=1, default=6)
    length: str = "800〜1500字"
    new_within_days: int = 30
    claude: ClaudeConfig = ClaudeConfig()
    fields: list[FieldConfig]
    max_candidates_per_field: int = 60


def load_config(path: Path | None = None) -> Config:
    path = path or ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Config.model_validate(raw)


def load_persona(path: Path | None = None) -> str:
    path = path or ROOT / "persona.md"
    return path.read_text(encoding="utf-8")
