"""Account balance parsing for the domestic stock mock account."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from config import Settings

if TYPE_CHECKING:
    from api_client import KISClient


def _to_int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", "")))
    except ValueError:
        return 0


@dataclass(frozen=True)
class AccountSnapshot:
    symbol_quantity: int
    available_cash: int
    average_price: int = 0


def get_account_snapshot(client: KISClient, settings: Settings) -> AccountSnapshot:
    payload = client.get(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        "VTTC8434R",
        {
            "CANO": settings.account_number,
            "ACNT_PRDT_CD": settings.account_product_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
    )

    holdings = payload.get("output1") or []
    symbol_rows = [
        item for item in holdings if str(item.get("pdno", "")).strip() == settings.symbol
    ]
    quantity = sum(_to_int(item.get("hldg_qty")) for item in symbol_rows)
    average_prices = [
        _to_int(item.get("pchs_avg_pric") or item.get("pchs_avg_price"))
        for item in symbol_rows
        if _to_int(item.get("pchs_avg_pric") or item.get("pchs_avg_price")) > 0
    ]
    average_price = average_prices[0] if average_prices else 0

    output2 = payload.get("output2") or {}
    if isinstance(output2, list):
        summary = output2[0] if output2 else {}
    elif isinstance(output2, dict):
        summary = output2
    else:
        summary = {}
    cash = _to_int(
        summary.get("dnca_tot_amt")
        or summary.get("prvs_rcdl_excc_amt")
        or summary.get("nass_amt")
    )
    return AccountSnapshot(
        symbol_quantity=quantity,
        available_cash=cash,
        average_price=average_price,
    )
