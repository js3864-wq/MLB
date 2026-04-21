"""Step 2 — Config loader."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SupplierFilters:
    min_orders: int
    min_rating: float
    min_stock: int


@dataclass(frozen=True)
class PipelineConfig:
    trend_category_count: int
    products_per_category: int
    recommendation_batch_size: int


@dataclass(frozen=True)
class ScoringConfig:
    platform_fee_rate: float
    return_rate: float


@dataclass(frozen=True)
class Config:
    supplier_filters: SupplierFilters
    pipeline: PipelineConfig
    scoring: ScoringConfig


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    raw = yaml.safe_load(path.read_text())
    return Config(
        supplier_filters=SupplierFilters(**raw["supplier_filters"]),
        pipeline=PipelineConfig(**raw["pipeline"]),
        scoring=ScoringConfig(**raw["scoring"]),
    )
