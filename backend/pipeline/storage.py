"""Supabase persistence + idempotent upserts keyed by (name, run_date)
for categories and (cj_product_id, run_date) for products.

If MOCK_MODE is on, reads/writes hit local JSON fixtures instead so the
frontend can be iterated against without a Supabase instance.
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock_data"


def mock_mode() -> bool:
    # DEMO_MODE implies offline storage too — no Supabase keys required.
    if os.environ.get("DEMO_MODE", "false").lower() == "true":
        return True
    return os.environ.get("MOCK_MODE", "false").lower() == "true"


# --------------------------- Supabase (real) ---------------------------

def _client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def upsert_trend_categories(names: list[str], run_date: date) -> list[dict[str, Any]]:
    if mock_mode():
        return _mock_upsert_categories(names, run_date)
    if not names:
        return []
    client = _client()
    rows = [{"name": n, "run_date": run_date.isoformat()} for n in names]
    resp = (
        client.table("trend_categories")
        .upsert(rows)
        .execute()
    )
    return resp.data or []


def upsert_products(products: list[dict[str, Any]], run_date: date) -> list[dict[str, Any]]:
    if mock_mode():
        return _mock_upsert_products(products, run_date)
    if not products:
        return []
    client = _client()
    payload = []
    for p in products:
        payload.append(
            {
                "category_id": p.get("category_id"),
                "cj_product_id": p["cj_product_id"],
                "title": p.get("title"),
                "image_url": p.get("image_url"),
                "supply_price": p.get("supply_price"),
                "sell_price": p.get("sell_price"),
                "shipping_cost": p.get("shipping_cost"),
                "platform_fee": p.get("platform_fee"),
                "net_margin": p.get("net_margin"),
                "margin_pct": p.get("margin_pct"),
                "supplier_risk_score": p.get("supplier_risk_score"),
                "sold_count": p.get("sold_count"),
                "stock": p.get("stock"),
                "supplier_rating": p.get("supplier_rating"),
                "recommendation": p.get("recommendation"),
                "explanation": p.get("explanation"),
                "run_date": run_date.isoformat(),
            }
        )
    resp = (
        client.table("products")
        .upsert(payload)
        .execute()
    )
    return resp.data or []


def fetch_trend_categories(run_date: date | None = None) -> list[dict[str, Any]]:
    if mock_mode():
        return _load_mock("trend_categories.json")
    client = _client()
    query = client.table("trend_categories").select("*")
    if run_date is not None:
        query = query.eq("run_date", run_date.isoformat())
    return query.order("created_at", desc=True).execute().data or []


def fetch_products(
    run_date: date | None = None, recommendation: str | None = None
) -> list[dict[str, Any]]:
    if mock_mode():
        items = _load_mock("products.json")
        if recommendation:
            items = [p for p in items if p.get("recommendation") == recommendation]
        return items
    client = _client()
    query = client.table("products").select("*")
    if run_date is not None:
        query = query.eq("run_date", run_date.isoformat())
    if recommendation is not None:
        query = query.eq("recommendation", recommendation)
    return query.order("margin_pct", desc=True).execute().data or []


def fetch_product(product_id: str) -> dict[str, Any] | None:
    if mock_mode():
        for p in _load_mock("products.json"):
            if p["id"] == product_id or p.get("cj_product_id") == product_id:
                return p
        return None
    client = _client()
    resp = client.table("products").select("*").eq("id", product_id).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


# ------------------------------ Mock IO ------------------------------

def _load_mock(name: str) -> list[dict[str, Any]]:
    path = MOCK_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _save_mock(name: str, rows: list[dict[str, Any]]) -> None:
    path = MOCK_DIR / name
    path.write_text(json.dumps(rows, indent=2))


def clear_mock_data() -> None:
    """Reset the mock JSON files. Used by DEMO_MODE so each run starts clean."""
    _save_mock("trend_categories.json", [])
    _save_mock("products.json", [])


def _mock_upsert_categories(names: list[str], run_date: date) -> list[dict[str, Any]]:
    existing = _load_mock("trend_categories.json")
    by_key = {(r["name"], r["run_date"]): r for r in existing}
    for i, n in enumerate(names):
        key = (n, run_date.isoformat())
        if key not in by_key:
            by_key[key] = {
                "id": f"c{len(by_key) + 1}",
                "name": n,
                "run_date": run_date.isoformat(),
            }
    merged = list(by_key.values())
    _save_mock("trend_categories.json", merged)
    return [r for r in merged if r["run_date"] == run_date.isoformat()]


def _mock_upsert_products(
    products: list[dict[str, Any]], run_date: date
) -> list[dict[str, Any]]:
    existing = _load_mock("products.json")
    by_key = {(r["cj_product_id"], r["run_date"]): r for r in existing}
    for p in products:
        key = (p["cj_product_id"], run_date.isoformat())
        by_key[key] = {
            **p,
            "run_date": run_date.isoformat(),
            "id": by_key.get(key, {}).get("id") or f"p{len(by_key) + 1}",
        }
    merged = list(by_key.values())
    _save_mock("products.json", merged)
    return [r for r in merged if r["run_date"] == run_date.isoformat()]
