"""Limit-order submission for mock domestic stock trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from api_client import KISClient
from config import Settings

OrderSide = Literal["buy", "sell"]

# KIS mock-trading cash order transaction IDs.
MOCK_ORDER_TR_IDS: dict[OrderSide, str] = {
    "buy": "VTTC0802U",
    "sell": "VTTC0801U",
}


@dataclass(frozen=True)
class OrderResult:
    side: OrderSide
    accepted: bool
    order_number: str
    message: str


def place_limit_order(
    client: KISClient,
    settings: Settings,
    side: OrderSide,
    price: int,
) -> OrderResult:
    tr_id = MOCK_ORDER_TR_IDS[side]
    payload = client.post(
        "/uapi/domestic-stock/v1/trading/order-cash",
        tr_id,
        {
            "CANO": settings.account_number,
            "ACNT_PRDT_CD": settings.account_product_code,
            "PDNO": settings.symbol,
            "ORD_DVSN": settings.order_division,
            "ORD_QTY": str(settings.order_quantity),
            "ORD_UNPR": str(price),
            "EXCG_ID_DVSN_CD": settings.exchange_code,
            "SLL_TYPE": "01" if side == "sell" else "",
            "CNDT_PRIC": "",
        },
    )
    output = payload.get("output") or {}
    return OrderResult(
        side=side,
        accepted=True,
        order_number=str(output.get("ODNO", "")),
        message=str(payload.get("msg1", "")),
    )
