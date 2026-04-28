"""Loader for `backend/demo_input.yaml` — used when DEMO_MODE=true.

Replaces Step 1 (pytrends + LLM) and Step 3 (CJ Dropshipping search) with
hand-curated inputs so the pipeline can run fully offline for a demo.
Steps 4 (margin math) and 5 (rules-based recommendation) still run, so the
dashboard shows numbers and verdicts derived from the values in the YAML.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .step3_products import ProductCandidate

DEFAULT_DEMO_PATH = Path(__file__).resolve().parents[1] / "demo_input.yaml"


@dataclass(frozen=True)
class DemoProduct:
    candidate: ProductCandidate
    category: str
    recommendation_override: str | None
    explanation_override: str | None


def demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "false").lower() == "true"


def load_demo_input(path: Path = DEFAULT_DEMO_PATH) -> tuple[list[str], list[DemoProduct]]:
    if not path.exists():
        raise FileNotFoundError(
            f"DEMO_MODE is on but {path} is missing. Create it or unset DEMO_MODE."
        )
    raw = yaml.safe_load(path.read_text()) or {}
    trends = [str(t).strip() for t in (raw.get("trends") or []) if str(t).strip()]
    if not trends:
        raise ValueError(f"{path}: `trends:` must list at least one category name.")

    valid_categories = set(trends)
    products: list[DemoProduct] = []
    for i, item in enumerate(raw.get("products") or []):
        category = str(item.get("category", "")).strip()
        if category not in valid_categories:
            raise ValueError(
                f"{path}: products[{i}] category {category!r} is not in `trends:`."
            )
        candidate = ProductCandidate(
            cj_product_id=str(item["cj_product_id"]),
            title=str(item.get("title", "")),
            image_url=str(item.get("image_url", "")),
            supply_price=float(item.get("supply_price", 0)),
            sell_price=float(item.get("sell_price", 0)),
            shipping_cost=float(item.get("shipping_cost", 0)),
            supplier_rating=float(item.get("supplier_rating", 0)),
            sold_count=int(item.get("sold_count", 0)),
            stock=int(item.get("stock", 0)),
        )
        rec = item.get("recommendation")
        rec_norm = str(rec).upper() if rec else None
        if rec_norm and rec_norm not in {"PURSUE", "MONITOR", "AVOID"}:
            raise ValueError(
                f"{path}: products[{i}] recommendation {rec!r} must be "
                "PURSUE, MONITOR, or AVOID."
            )
        products.append(
            DemoProduct(
                candidate=candidate,
                category=category,
                recommendation_override=rec_norm,
                explanation_override=item.get("explanation"),
            )
        )
    return trends, products
