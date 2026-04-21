"""Smoke test: run Step 1 + Step 3 only and print raw CJ fields.

Use this BEFORE wiring up the rest of the pipeline to confirm that
`sellPrice` is actually present on CJ product search responses. If
this script prints non-zero sellPrice values for a handful of products,
the rest of the pipeline is safe to build on top.

Run: python -m backend.scripts.verify_cj_sellprice
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running as a script from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

from backend.pipeline.cj_client import CJClient, credentials_from_env
from backend.pipeline.step1_trends import run as run_step1
from backend.pipeline.step2_config import load_config
from backend.pipeline.step3_products import normalize_product


async def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    cfg = load_config()

    print("=== Step 1: fetching trend categories ===")
    try:
        categories = run_step1()
    except Exception as exc:  # pragma: no cover - smoke test
        print(f"Step 1 failed: {exc}")
        print("Falling back to a hardcoded category list.")
        categories = ["ergonomic lumbar cushion", "portable blender", "pet grooming glove"]
    print(f"Got {len(categories)} categories:")
    for c in categories:
        print(f"  - {c}")

    # Only probe the first 2 categories to keep API usage low.
    probe = categories[:2]

    print("\n=== Step 3: probing CJ product search ===")
    creds = credentials_from_env()
    async with CJClient(creds) as cj:
        for category in probe:
            print(f"\n--- category: {category!r} ---")
            raw_list = await cj.search_products(category, page_size=5)
            if not raw_list:
                print("  (no results)")
                continue
            for raw in raw_list:
                pid = raw.get("pid") or raw.get("productId")
                sell = raw.get("sellPrice") or raw.get("suggestSellPrice")
                supply = raw.get("supplyPrice") or raw.get("productPrice")
                title = (raw.get("productNameEn") or raw.get("productName") or "")[:60]
                print(
                    f"  pid={pid} supply={supply} sell={sell}  title={title!r}"
                )
                if not sell:
                    print("    !! sellPrice missing — investigate API response:")
                    print("    " + json.dumps(raw, indent=2)[:500])

            normalized = normalize_product(raw_list[0], shipping_cost=0.0)
            print(f"  -> normalized: {normalized}")

    print("\nDone. If sellPrice values above are non-zero, Step 3 is good to go.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
