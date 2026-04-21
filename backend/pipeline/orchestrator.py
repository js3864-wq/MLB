"""End-to-end pipeline runner.

Calls Step 1 -> Step 3 -> Step 4 -> Step 5, persists to Supabase
(or mock JSON), and returns a run summary. Respects MOCK_MODE so the
frontend can be iterated against without hitting any real APIs.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from . import step1_trends, step4_enrich, step5_recommend, storage
from .step2_config import Config, load_config

log = logging.getLogger(__name__)


def _mock_categories() -> list[str]:
    return [c["name"] for c in storage._load_mock("trend_categories.json")]


def _mock_products(category_id_by_name: dict[str, str]) -> list[dict[str, Any]]:
    products = storage._load_mock("products.json")
    # Re-point category_id in case we generated fresh UUIDs during this run.
    name_by_old_id = {
        c["id"]: c["name"] for c in storage._load_mock("trend_categories.json")
    }
    for p in products:
        old = p.get("category_id")
        name = name_by_old_id.get(old)
        if name and name in category_id_by_name:
            p["category_id"] = category_id_by_name[name]
    return products


async def run_pipeline(run_date: date | None = None) -> dict[str, Any]:
    run_date = run_date or date.today()
    cfg: Config = load_config()
    mock = storage.mock_mode()
    log.info("Starting pipeline run_date=%s mock=%s", run_date, mock)

    # --- Step 1 -------------------------------------------------------
    if mock:
        categories = _mock_categories()
    else:
        categories = step1_trends.run()
    categories = categories[: cfg.pipeline.trend_category_count]
    saved_cats = storage.upsert_trend_categories(categories, run_date)
    cat_id_by_name = {c["name"]: c["id"] for c in saved_cats}
    log.info("Step 1: %d categories", len(saved_cats))

    # --- Step 3 -------------------------------------------------------
    if mock:
        candidates = _mock_products(cat_id_by_name)
    else:
        from .cj_client import CJClient, credentials_from_env  # lazy
        from .step3_products import find_products_for_category  # lazy

        candidates = []
        creds = credentials_from_env()
        async with CJClient(creds) as cj:
            for cat_name in categories:
                cat_id = cat_id_by_name.get(cat_name)
                products = await find_products_for_category(
                    cj, cat_name, cfg.supplier_filters, cfg.pipeline.products_per_category
                )
                for p in products:
                    row = p.to_dict()
                    row["category_id"] = cat_id
                    candidates.append(row)
    log.info("Step 3: %d candidate products", len(candidates))

    # --- Step 4 -------------------------------------------------------
    if mock:
        enriched = candidates  # mock fixtures are already enriched
    else:
        from .step3_products import ProductCandidate  # lazy

        enriched = []
        for c in candidates:
            pc = ProductCandidate(
                cj_product_id=c["cj_product_id"],
                title=c["title"],
                image_url=c["image_url"],
                supply_price=c["supply_price"],
                sell_price=c["sell_price"],
                shipping_cost=c["shipping_cost"],
                supplier_rating=c.get("supplier_rating", 0.0),
                sold_count=c.get("sold_count", 0),
                stock=c.get("stock", 0),
            )
            merged = {**c, **step4_enrich.enrich(pc, cfg.scoring)}
            enriched.append(merged)
    log.info("Step 4: enriched %d products", len(enriched))

    # --- Step 5 -------------------------------------------------------
    if mock:
        recommended = enriched  # fixtures carry recommendation + explanation
    else:
        recommended = step5_recommend.recommend_all(
            enriched, batch_size=cfg.pipeline.recommendation_batch_size
        )
    log.info("Step 5: recommendations generated")

    saved_products = storage.upsert_products(recommended, run_date)
    return {
        "run_date": run_date.isoformat(),
        "categories": len(saved_cats),
        "products": len(saved_products),
        "mock_mode": mock,
    }
