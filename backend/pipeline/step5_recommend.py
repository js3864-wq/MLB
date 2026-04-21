"""Step 5 — Claude recommendation per product (batched)."""
from __future__ import annotations

import json
import os
from typing import Any

CLAUDE_MODEL = "claude-sonnet-4-5"

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
    from anthropic import Anthropic  # lazy import

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    numbered = "\n\n".join(
        f"Product {i + 1}:\n{_format_product(p)}" for i, p in enumerate(products)
    )
    user_content = (
        f"Analyze these {len(products)} products. Respond with a JSON array of "
        f"{len(products)} objects in the same order.\n\n{numbered}"
    )
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
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
