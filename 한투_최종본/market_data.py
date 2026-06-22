"""Domestic stock market-data functions."""

from __future__ import annotations

from api_client import KISClient, KISAPIError
from config import Settings


def get_current_price(client: KISClient, settings: Settings) -> int:
    payload = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        "FHKST01010100",
        {
            "FID_COND_MRKT_DIV_CODE": settings.market_code,
            "FID_INPUT_ISCD": settings.symbol,
        },
    )
    output = payload.get("output") or {}
    raw_price = output.get("stck_prpr")
    try:
        price = int(raw_price)
    except (TypeError, ValueError) as exc:
        raise KISAPIError(f"Unexpected current-price response: {output}") from exc
    if price <= 0:
        raise KISAPIError(f"Current price must be positive, got {price}")
    return price

