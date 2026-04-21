"""Step 4 — Enrich product data with risk score and margin fields."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .step2_config import ScoringConfig
from .step3_products import ProductCandidate


def supplier_risk_score(p: ProductCandidate) -> float:
    rating_part = (p.supplier_rating / 5.0) * 40.0
    volume_part = (min(p.sold_count, 1000) / 1000.0) * 40.0
    stock_part = (min(p.stock, 200) / 200.0) * 20.0
    return round(rating_part + volume_part + stock_part, 2)


def enrich(p: ProductCandidate, scoring: ScoringConfig) -> dict[str, Any]:
    platform_fee = round(p.sell_price * scoring.platform_fee_rate, 2)
    return_reserve = round(p.sell_price * scoring.return_rate, 2)
    net_margin = round(
        p.sell_price - p.supply_price - p.shipping_cost - platform_fee - return_reserve, 2
    )
    margin_pct = round((net_margin / p.sell_price) * 100.0, 2) if p.sell_price else 0.0
    risk = supplier_risk_score(p)
    out = p.to_dict()
    out.update(
        {
            "platform_fee": platform_fee,
            "net_margin": net_margin,
            "margin_pct": margin_pct,
            "supplier_risk_score": risk,
        }
    )
    return out
