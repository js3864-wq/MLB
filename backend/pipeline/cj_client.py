"""Thin async CJ Dropshipping API client.

CJ uses a two-step auth flow: POST /authentication/getAccessToken with
{email, password} returns an accessToken that must be sent as
`CJ-Access-Token` on subsequent calls. Tokens last ~15 days.

Docs: https://developers.cjdropshipping.com/en/api/
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"


@dataclass
class CJCredentials:
    email: str
    api_key: str


class CJClient:
    def __init__(self, creds: CJCredentials, timeout: float = 30.0):
        self._creds = creds
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=timeout, base_url=CJ_BASE)

    async def __aenter__(self) -> "CJClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        resp = await self._http.post(
            "/authentication/getAccessToken",
            json={"email": self._creds.email, "password": self._creds.api_key},
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("result"):
            raise RuntimeError(f"CJ auth failed: {body.get('message')}")
        data = body["data"]
        self._token = data["accessToken"]
        # CJ returns `accessTokenExpiryDate` in seconds or an ISO timestamp
        # depending on the endpoint version; default to 14 days if missing.
        self._token_expires_at = time.time() + 14 * 24 * 3600
        return self._token

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        token = await self._ensure_token()
        resp = await self._http.get(
            path, params=params, headers={"CJ-Access-Token": token}
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("result"):
            raise RuntimeError(f"CJ {path} failed: {body.get('message')}")
        return body["data"]

    async def search_products(
        self, keyword: str, page: int = 1, page_size: int = 20
    ) -> list[dict[str, Any]]:
        """Return raw product dicts from CJ product list search."""
        data = await self._get(
            "/product/list",
            {"productNameEn": keyword, "pageNum": page, "pageSize": page_size},
        )
        return data.get("list", [])

    async def product_details(self, product_id: str) -> dict[str, Any]:
        return await self._get("/product/query", {"pid": product_id})

    async def freight_estimate(
        self, product_id: str, country: str = "US", quantity: int = 1
    ) -> float | None:
        """Return the cheapest shipping cost to the given country."""
        try:
            data = await self._get(
                "/logistic/freightCalculate",
                {"productId": product_id, "countryCode": country, "quantity": quantity},
            )
        except (RuntimeError, httpx.HTTPStatusError):
            return None
        options = data if isinstance(data, list) else data.get("list", [])
        if not options:
            return None
        return min(float(o["logisticPrice"]) for o in options if o.get("logisticPrice"))


def credentials_from_env() -> CJCredentials:
    email = os.environ.get("CJ_API_EMAIL")
    api_key = os.environ.get("CJ_API_KEY")
    if not email or not api_key:
        raise RuntimeError("CJ_API_EMAIL and CJ_API_KEY must be set in .env")
    return CJCredentials(email=email, api_key=api_key)
