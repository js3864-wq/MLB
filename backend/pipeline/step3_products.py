"""Step 3 — Find Potential Products on CJ Dropshipping.

For each trend category we pull products from CJ, normalize the fields
we care about, and apply the supplier filters from config.yaml.

IMPORTANT: CJ's raw field names differ between list and detail responses,
so the normalizer here is intentionally defensive. `sellPrice` is CJ's
suggested retail price — that's what we use as the estimated retail
price. `supplyPrice` (or `sellPrice` on the detail endpoint's "cost"
variant) is our cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .step2_config import SupplierFilters

if TYPE_CHECKING:
    from .cj_client import CJClient


@dataclass
class ProductCandidate:
    cj_product_id: str
    title: str
    image_url: str
    supply_price: float
    sell_price: float  # CJ suggested retail
    shipping_cost: float
    supplier_rating: float
    sold_count: int
    stock: int

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _as_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        # CJ occasionally returns price ranges like "9.99-12.99" — take the low end.
        if isinstance(val, str) and "-" in val:
            val = val.split("-", 1)[0]
        return float(val)
    except (TypeError, ValueError):
        return default


def _as_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def normalize_product(raw: dict[str, Any], shipping_cost: float) -> ProductCandidate:
    """Map a raw CJ product dict to our canonical shape.

    CJ's product list response uses camelCase; names vary slightly across
    versions so we try a few keys per field.
    """
    pid = str(raw.get("pid") or raw.get("productId") or "")
    title = raw.get("productNameEn") or raw.get("productName") or ""
    image = raw.get("productImage") or raw.get("productImageSet", [""])[0] or ""
    # "sellPrice" on CJ = suggested retail. "productPrice" or "supplyPrice"
    # can show up as our cost depending on endpoint.
    supply_price = _as_float(raw.get("supplyPrice") or raw.get("productPrice"))
    sell_price = _as_float(raw.get("sellPrice") or raw.get("suggestSellPrice"))
    rating = _as_float(raw.get("supplierRating") or raw.get("score") or raw.get("productRating"))
    sold = _as_int(raw.get("soldCount") or raw.get("listedNum") or raw.get("saleNum"))
    stock = _as_int(raw.get("productStock") or raw.get("stock") or raw.get("inventory"))
    return ProductCandidate(
        cj_product_id=pid,
        title=title,
        image_url=image,
        supply_price=supply_price,
        sell_price=sell_price,
        shipping_cost=shipping_cost,
        supplier_rating=rating,
        sold_count=sold,
        stock=stock,
    )


def passes_filters(p: ProductCandidate, f: SupplierFilters) -> bool:
    if p.sell_price <= p.supply_price:
        return False  # no margin possible
    if p.sold_count < f.min_orders:
        return False
    if p.supplier_rating < f.min_rating:
        return False
    if p.stock < f.min_stock:
        return False
    return True


async def find_products_for_category(
    client: "CJClient",
    category: str,
    filters: SupplierFilters,
    page_size: int = 20,
) -> list[ProductCandidate]:
    raw_list = await client.search_products(category, page=1, page_size=page_size)
    candidates: list[ProductCandidate] = []
    for raw in raw_list:
        pid = str(raw.get("pid") or raw.get("productId") or "")
        if not pid:
            continue
        shipping = await client.freight_estimate(pid) or 0.0
        product = normalize_product(raw, shipping_cost=shipping)
        if passes_filters(product, filters):
            candidates.append(product)
    return candidates
