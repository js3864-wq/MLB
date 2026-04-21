"""Step 1 — Identify Product Trends.

Pulls rising queries from Google Trends via pytrends, feeds them into a
single Claude call, and returns 10 specific product-category names.
"""
from __future__ import annotations

import json
import os
from typing import Iterable

CLAUDE_MODEL = "claude-sonnet-4-5"

# Seed keywords used to pull rising related queries. We intentionally keep
# this broad — the Claude call is responsible for narrowing to specific,
# dropshipping-friendly product categories.
SEED_KEYWORDS = [
    "home gadgets",
    "fitness accessories",
    "pet products",
    "kitchen tools",
    "office accessories",
]

CATEGORY_PROMPT = (
    "Given these trending search queries, return a JSON array of 10 specific "
    "product category names that are likely profitable for dropshipping. Be as "
    "specific as possible (e.g. 'ergonomic lumbar cushion' not 'cushions'). "
    "Return only valid JSON."
)


def fetch_rising_queries(
    keywords: Iterable[str] = SEED_KEYWORDS, geo: str = "US"
) -> list[str]:
    from pytrends.request import TrendReq  # imported lazily so MOCK_MODE works without the dep

    pytrends = TrendReq(hl="en-US", tz=360)
    rising: list[str] = []
    for kw in keywords:
        try:
            pytrends.build_payload([kw], timeframe="now 7-d", geo=geo)
            related = pytrends.related_queries().get(kw) or {}
            frame = related.get("rising")
            if frame is None or frame.empty:
                continue
            rising.extend(frame["query"].head(10).tolist())
        except Exception:
            # pytrends is notoriously flaky; skip and move on.
            continue
    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in rising:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def categories_from_queries(queries: list[str]) -> list[str]:
    from anthropic import Anthropic  # lazy import

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_content = CATEGORY_PROMPT + "\n\nQueries:\n" + "\n".join(f"- {q}" for q in queries)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    # Claude may wrap JSON in prose despite the instruction; grab the array.
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"Claude did not return a JSON array: {text!r}")
    categories = json.loads(text[start : end + 1])
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise ValueError(f"Unexpected category payload: {categories!r}")
    return categories


def run() -> list[str]:
    queries = fetch_rising_queries()
    if not queries:
        # Fall back to the seed keywords if Trends gave us nothing.
        queries = list(SEED_KEYWORDS)
    return categories_from_queries(queries)
