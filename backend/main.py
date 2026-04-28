"""FastAPI app exposing the pipeline + read APIs for the Next.js dashboard.

Run: uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env")

from .pipeline import demo_loader, storage  # noqa: E402
from .pipeline.orchestrator import run_pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("dropship")

scheduler = AsyncIOScheduler()


async def _scheduled_run() -> None:
    try:
        result = await run_pipeline()
        log.info("Scheduled pipeline complete: %s", result)
    except Exception:
        log.exception("Scheduled pipeline run failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.add_job(_scheduled_run, "cron", hour=6, minute=0, id="daily-pipeline")
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Dropshipping Product Finder", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "mock_mode": storage.mock_mode(),
        "demo_mode": demo_loader.demo_mode(),
    }


@app.post("/run-pipeline")
async def trigger_pipeline() -> dict[str, Any]:
    """Manually trigger a full pipeline run (useful during development)."""
    return await run_pipeline()


@app.get("/trends")
async def list_trends(run_date: date | None = Query(default=None)) -> dict[str, Any]:
    cats = storage.fetch_trend_categories(run_date)
    products = storage.fetch_products(run_date)
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for p in products:
        by_cat.setdefault(p.get("category_id") or "", []).append(p)
    enriched = []
    for c in cats:
        group = by_cat.get(c["id"], [])
        margins = [p["margin_pct"] for p in group if p.get("margin_pct") is not None]
        avg_margin = round(sum(margins) / len(margins), 2) if margins else 0.0
        enriched.append(
            {
                **c,
                "product_count": len(group),
                "avg_margin_pct": avg_margin,
            }
        )
    return {"categories": enriched}


@app.get("/products")
async def list_products(
    run_date: date | None = Query(default=None),
    recommendation: str | None = Query(default=None),
) -> dict[str, Any]:
    rows = storage.fetch_products(run_date=run_date, recommendation=recommendation)
    return {"products": rows}


@app.get("/products/{product_id}")
async def product_detail(product_id: str) -> dict[str, Any]:
    p = storage.fetch_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p
