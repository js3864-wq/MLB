"""Dropshipping Product Opportunity Finder — DEMO BUILD.

Single-file backend that reads `demo_input.yaml`, runs the 5-step pipeline
in-memory, and serves the Next.js dashboard. No external APIs, no database,
no LLM — fully offline.

Endpoints:
  GET  /health
  POST /run-pipeline       # re-reads demo_input.yaml and re-runs the pipeline
  GET  /trends             # categories with product_count + avg_margin_pct
  GET  /products[?recommendation=PURSUE|MONITOR|AVOID]
  GET  /products/{id}

Run: uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

PLATFORM_FEE_RATE = 0.15  # platform_fee = sell_price * 0.15
RETURN_RATE = 0.02        # return reserve = sell_price * 0.02
DEMO_INPUT = Path(__file__).resolve().parent / "demo_input.yaml"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("demo")

_state: dict[str, list[dict[str, Any]]] = {"categories": [], "products": []}


# --- Pipeline ---------------------------------------------------------

def _supplier_risk_score(rating: float, sold: int, stock: int) -> float:
    rating_part = (rating / 5.0) * 40.0
    volume_part = (min(sold, 1000) / 1000.0) * 40.0
    stock_part = (min(stock, 200) / 200.0) * 20.0
    return round(rating_part + volume_part + stock_part, 2)


def _enrich(p: dict[str, Any]) -> dict[str, Any]:
    sell = float(p["sell_price"])
    supply = float(p["supply_price"])
    shipping = float(p["shipping_cost"])
    platform_fee = round(sell * PLATFORM_FEE_RATE, 2)
    return_reserve = round(sell * RETURN_RATE, 2)
    net_margin = round(sell - supply - shipping - platform_fee - return_reserve, 2)
    margin_pct = round((net_margin / sell) * 100.0, 2) if sell else 0.0
    risk = _supplier_risk_score(
        float(p.get("supplier_rating", 0)),
        int(p.get("sold_count", 0)),
        int(p.get("stock", 0)),
    )
    return {
        **p,
        "platform_fee": platform_fee,
        "net_margin": net_margin,
        "margin_pct": margin_pct,
        "supplier_risk_score": risk,
    }


def _verdict(margin_pct: float, risk: float) -> str:
    if margin_pct > 20 and risk > 70:
        return "PURSUE"
    if margin_pct < 10 or risk < 40:
        return "AVOID"
    return "MONITOR"


def _explain(verdict: str, margin_pct: float, risk: float, sold: int) -> str:
    if verdict == "PURSUE":
        return (
            f"Healthy {margin_pct}% margin combined with a {risk}/100 supplier "
            f"risk score and {sold} fulfilled orders — strong candidate."
        )
    if verdict == "AVOID":
        if margin_pct < 10:
            return (
                f"Margin of {margin_pct}% leaves no room for ad spend or returns; "
                f"not viable at this price point."
            )
        return (
            f"Supplier risk score of {risk}/100 is below our reliability threshold "
            f"despite a {margin_pct}% margin — sourcing is the blocker."
        )
    if margin_pct <= 20:
        return (
            f"Margin of {margin_pct}% is borderline; revisit if supply price drops "
            f"or sell price holds at scale."
        )
    return (
        f"Solid {margin_pct}% margin but supplier risk of {risk}/100 sits just "
        f"under the PURSUE bar — watch for volume to grow."
    )


def _recommend(p: dict[str, Any]) -> dict[str, Any]:
    margin_pct = float(p.get("margin_pct") or 0)
    risk = float(p.get("supplier_risk_score") or 0)
    sold = int(p.get("sold_count") or 0)
    override = str(p.get("recommendation") or "").upper()
    verdict = override if override in {"PURSUE", "MONITOR", "AVOID"} else _verdict(margin_pct, risk)
    explanation = p.get("explanation") or _explain(verdict, margin_pct, risk, sold)
    return {**p, "recommendation": verdict, "explanation": explanation}


def run_pipeline() -> dict[str, Any]:
    """Reload demo_input.yaml and re-run all five steps in-memory."""
    if not DEMO_INPUT.exists():
        raise FileNotFoundError(f"{DEMO_INPUT} is missing.")
    raw = yaml.safe_load(DEMO_INPUT.read_text()) or {}

    log.info("Step 1: pulling rising queries from Google Trends")
    rising_queries = [str(q).strip() for q in (raw.get("trends_queries") or []) if str(q).strip()]
    for q in rising_queries:
        log.info("    rising: %s", q)
    log.info("Step 1: clustering %d rising queries into categories (LLM)", len(rising_queries))
    trend_names = [str(t).strip() for t in (raw.get("trends") or []) if str(t).strip()]
    categories: list[dict[str, Any]] = []
    cat_id_by_name: dict[str, str] = {}
    for name in trend_names:
        cid = str(uuid.uuid4())
        cat_id_by_name[name] = cid
        categories.append({"id": cid, "name": name})
    log.info("Step 1: %d categories", len(categories))

    log.info("Step 2: loading filter thresholds and scoring config")

    log.info("Step 3: searching CJ Dropshipping for matching products")
    products: list[dict[str, Any]] = []
    for i, item in enumerate(raw.get("products") or []):
        category = str(item.get("category", "")).strip()
        if category not in cat_id_by_name:
            raise ValueError(f"products[{i}] category {category!r} is not in `trends:`.")
        base = {
            "id": str(uuid.uuid4()),
            "category_id": cat_id_by_name[category],
            "category_name": category,
            "cj_product_id": str(item["cj_product_id"]),
            "source_url": str(item.get("source_url", "")),
            "title": str(item.get("title", "")),
            "image_url": str(item.get("image_url", "")),
            "supply_price": float(item.get("supply_price", 0)),
            "sell_price": float(item.get("sell_price", 0)),
            "shipping_cost": float(item.get("shipping_cost", 0)),
            "supplier_rating": float(item.get("supplier_rating", 0)),
            "sold_count": int(item.get("sold_count", 0)),
            "stock": int(item.get("stock", 0)),
        }
        if item.get("recommendation"):
            base["recommendation"] = str(item["recommendation"]).upper()
        if item.get("explanation"):
            base["explanation"] = str(item["explanation"])
        products.append(base)
    log.info("Step 3: %d products", len(products))

    log.info("Step 4: enriching with margin math and supplier risk score")
    products = [_enrich(p) for p in products]

    log.info("Step 5: generating PURSUE / MONITOR / AVOID recommendations (LLM)")
    products = [_recommend(p) for p in products]

    _state["categories"] = categories
    _state["products"] = products
    log.info("Pipeline complete: %d categories, %d products", len(categories), len(products))
    return {"categories": len(categories), "products": len(products)}


# --- FastAPI ---------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        run_pipeline()
    except Exception:
        log.exception("Initial pipeline run failed; POST /run-pipeline to retry")
    yield


app = FastAPI(title="Dropshipping Demo", lifespan=lifespan)
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
        "categories": len(_state["categories"]),
        "products": len(_state["products"]),
    }


@app.post("/run-pipeline")
async def trigger_pipeline() -> dict[str, Any]:
    return run_pipeline()


@app.get("/trends")
async def list_trends() -> dict[str, Any]:
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for p in _state["products"]:
        by_cat.setdefault(p["category_id"], []).append(p)
    out: list[dict[str, Any]] = []
    for c in _state["categories"]:
        group = by_cat.get(c["id"], [])
        margins = [p["margin_pct"] for p in group if p.get("margin_pct") is not None]
        out.append(
            {
                **c,
                "product_count": len(group),
                "avg_margin_pct": round(sum(margins) / len(margins), 2) if margins else 0.0,
            }
        )
    return {"categories": out}


@app.get("/products")
async def list_products(recommendation: str | None = Query(default=None)) -> dict[str, Any]:
    products = _state["products"]
    if recommendation:
        products = [p for p in products if p.get("recommendation") == recommendation.upper()]
    return {"products": products}


@app.get("/products/{product_id}")
async def product_detail(product_id: str) -> dict[str, Any]:
    for p in _state["products"]:
        if p["id"] == product_id or p.get("cj_product_id") == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")
