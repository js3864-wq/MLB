"""Step 5 — Claude recommendation per product (batched)."""
from __future__ import annotations

import json
import os
from typing import Any

AZURE_DEPLOYMENT = os.environ.get("AZURE_FOUNDRY_DEPLOYMENT", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are a dropshipping analyst. For each product you receive, output a JSON "
    "object with two fields: 'recommendation' (one of: PURSUE, MONITOR, AVOID) and "
    "'explanation' (1-2 sentence plain English reason).\n\n"
    "Rules:\n"
    "- PURSUE: margin_pct > 20 AND supplier_risk_score > 70\n"
    "- AVOID: margin_pct < 10 OR supplier_risk_score < 40\n"
    "- MONITOR: everything else\n\n"
    "Return only valid JSON — a JSON array when you receive multiple products, "
    "or a single JSON object for one product. No prose outside the JSON."
)


def _format_product(p: dict[str, Any]) -> str:
    return (
        f"- Title: {p['title']}\n"
        f"- CJ Supply Price: ${p['supply_price']}\n"
        f"- CJ Estimated Retail: ${p['sell_price']}\n"
        f"- Net Margin: ${p['net_margin']} ({p['margin_pct']}%)\n"
        f"- Supplier Risk Score: {p['supplier_risk_score']}/100\n"
        f"- Fulfilled Orders: {p['sold_count']}\n"
        f"- Stock: {p['stock']}"
    )


def _extract_json(text: str) -> Any:
    # Claude sometimes wraps JSON in ```json fences; strip and locate.
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    # Prefer an array, fall back to object.
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Claude response was not valid JSON: {text!r}")


def recommend_batch(products: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Call Claude once for up to ~10 products; return a recommendation per item, in order."""
    if not products:
        return []
    from openai import OpenAI  # lazy import

    client = OpenAI(
        base_url=os.environ["AZURE_FOUNDRY_BASE_URL"],
        api_key=os.environ["AZURE_FOUNDRY_API_KEY"],
    )
    numbered = "\n\n".join(
        f"Product {i + 1}:\n{_format_product(p)}" for i, p in enumerate(products)
    )
    user_content = (
        f"Analyze these {len(products)} products. Respond with a JSON array of "
        f"{len(products)} objects in the same order.\n\n{numbered}"
    )
    resp = client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    text = resp.choices[0].message.content or ""
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list) or len(parsed) != len(products):
        raise ValueError(
            f"Expected {len(products)} recommendations, got: {parsed!r}"
        )
    out: list[dict[str, str]] = []
    for item in parsed:
        rec = str(item.get("recommendation", "")).upper()
        if rec not in {"PURSUE", "MONITOR", "AVOID"}:
            rec = "MONITOR"
        out.append(
            {"recommendation": rec, "explanation": str(item.get("explanation", ""))}
        )
    return out


def recommend_all(
    products: list[dict[str, Any]], batch_size: int = 10
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i in range(0, len(products), batch_size):
        chunk = products[i : i + batch_size]
        recs = recommend_batch(chunk)
        for p, r in zip(chunk, recs):
            merged = {**p, **r}
            results.append(merged)
    return results


# --- Offline / DEMO_MODE: rules-based recommendation, no LLM ---------

def _verdict_from_rules(margin_pct: float, risk: float) -> str:
    if margin_pct > 20 and risk > 70:
        return "PURSUE"
    if margin_pct < 10 or risk < 40:
        return "AVOID"
    return "MONITOR"


def _explain(verdict: str, margin_pct: float, risk: float, sold: int) -> str:
    if verdict == "PURSUE":
        return (
            f"Healthy {margin_pct}% margin combined with a {risk}/100 supplier risk "
            f"score and {sold} fulfilled orders — strong candidate."
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


def recommend_rule_based(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute PURSUE/MONITOR/AVOID + explanation from the rules. No API calls.

    Each input dict may carry `recommendation` and/or `explanation` to override
    the computed values (used by demo_input.yaml's manual override).
    """
    out: list[dict[str, Any]] = []
    for p in products:
        margin_pct = float(p.get("margin_pct") or 0)
        risk = float(p.get("supplier_risk_score") or 0)
        sold = int(p.get("sold_count") or 0)
        override = p.get("recommendation")
        verdict = (
            str(override).upper()
            if override in {"PURSUE", "MONITOR", "AVOID"}
            else _verdict_from_rules(margin_pct, risk)
        )
        explanation = p.get("explanation") or _explain(verdict, margin_pct, risk, sold)
        out.append({**p, "recommendation": verdict, "explanation": explanation})
    return out
