"""One-shot KIS mock-investment runner using only Python standard library.

Use this when `requests` cannot be installed. It reads `.env`, issues an access
token, queries current price and balance, then prints the finance strategy
decision. If `DRY_RUN=false`, it submits the selected mock order.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from account import AccountSnapshot
from config import SEOUL_TZ, Settings
from strategy import decide_action


BASE_URL = "https://openapivts.koreainvestment.com:29443"
PROJECT_DIR = Path(__file__).resolve().parent
TOKEN_CACHE = PROJECT_DIR / "token_cache.json"


def load_env(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing .env file: {path}")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def split_account(account: str) -> tuple[str, str]:
    normalized = account.replace("-", "").strip()
    if len(normalized) != 10 or not normalized.isdigit():
        raise ValueError("GH_ACCOUNT must look like 12345678-01")
    return normalized[:8], normalized[8:]


def request_json(method: str, url: str, headers=None, params=None, body=None):
    headers = headers or {}
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    payload = json.loads(raw)
    if payload.get("rt_cd") not in (None, "0"):
        raise RuntimeError(f"KIS API error {payload.get('msg_cd')}: {payload.get('msg1')}")
    time.sleep(0.5)
    return payload


def issue_token(app_key: str, app_secret: str) -> str:
    today = datetime.now(SEOUL_TZ).date().isoformat()
    if TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            if cached.get("issued_date") == today and cached.get("access_token"):
                print("token_reused: true")
                return str(cached["access_token"])
        except (OSError, json.JSONDecodeError):
            pass

    payload = request_json(
        "POST",
        f"{BASE_URL}/oauth2/tokenP",
        headers={"content-type": "application/json; charset=utf-8"},
        body={
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret,
        },
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Token response missing access_token: {payload}")
    TOKEN_CACHE.write_text(
        json.dumps(
            {
                "access_token": token,
                "issued_date": today,
                "expires_at": payload.get("access_token_token_expired"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(token)


def headers(token: str, app_key: str, app_secret: str, tr_id: str) -> dict[str, str]:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }


def get_price(token: str, app_key: str, app_secret: str, symbol: str) -> int:
    payload = request_json(
        "GET",
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers(token, app_key, app_secret, "FHKST01010100"),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
        },
    )
    return int(payload["output"]["stck_prpr"])


def get_balance(
    token: str,
    app_key: str,
    app_secret: str,
    account_no: str,
    product_code: str,
    symbol: str,
) -> AccountSnapshot:
    payload = request_json(
        "GET",
        f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers=headers(token, app_key, app_secret, "VTTC8434R"),
        params={
            "CANO": account_no,
            "ACNT_PRDT_CD": product_code,
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

    def to_int(value) -> int:
        try:
            return int(float(str(value or "0").replace(",", "")))
        except ValueError:
            return 0

    rows = [row for row in holdings if str(row.get("pdno", "")).strip() == symbol]
    quantity = sum(to_int(row.get("hldg_qty")) for row in rows)
    avg = 0
    if rows:
        avg = to_int(rows[0].get("pchs_avg_pric") or rows[0].get("pchs_avg_price"))
    output2 = payload.get("output2") or {}
    if isinstance(output2, list):
        output2 = output2[0] if output2 else {}
    cash = to_int(output2.get("dnca_tot_amt") or output2.get("prvs_rcdl_excc_amt") or output2.get("nass_amt"))
    return AccountSnapshot(symbol_quantity=quantity, available_cash=cash, average_price=avg)


def submit_order(
    token: str,
    app_key: str,
    app_secret: str,
    account_no: str,
    product_code: str,
    symbol: str,
    side: str,
    quantity: int,
    price: int,
    order_division: str,
):
    tr_id = "VTTC0802U" if side == "buy" else "VTTC0801U"
    return request_json(
        "POST",
        f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
        headers=headers(token, app_key, app_secret, tr_id),
        body={
            "CANO": account_no,
            "ACNT_PRDT_CD": product_code,
            "PDNO": symbol,
            "ORD_DVSN": order_division,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        },
    )


def main() -> None:
    load_env(PROJECT_DIR / ".env")
    account_no, product_code = split_account(os.environ["GH_ACCOUNT"])
    app_key = os.environ["GH_APPKEY"]
    app_secret = os.environ["GH_APPSECRET"]
    symbol = os.getenv("SYMBOL", "005930")
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    order_division = os.getenv("ORDER_DIVISION", "00")
    quantity = int(os.getenv("ORDER_QUANTITY", "1"))

    token = issue_token(app_key, app_secret)
    print("token_issued: true")
    price = get_price(token, app_key, app_secret, symbol)
    print(f"current_price[{symbol}]: {price:,}")
    snapshot = get_balance(token, app_key, app_secret, account_no, product_code, symbol)
    print(
        "balance:",
        f"quantity={snapshot.symbol_quantity}",
        f"cash={snapshot.available_cash:,}",
        f"average_price={snapshot.average_price:,}",
    )

    settings = Settings(
        app_key=app_key,
        app_secret=app_secret,
        account_number=account_no,
        account_product_code=product_code,
        symbol=symbol,
        dry_run=dry_run,
        order_quantity=quantity,
        order_division=order_division,
    )
    decision = decide_action(current_price=price, snapshot=snapshot, settings=settings)
    print(
        "decision:",
        f"action={decision.action}",
        f"buy_price={decision.buy_price:,}",
        f"sell_price={decision.sell_price:,}",
        f"expected_return={decision.expected_return:.4%}",
        f"loss_probability={decision.loss_probability:.2%}",
        f"reason={decision.reason}",
    )
    if decision.action in {"buy", "sell"} and not dry_run:
        order_price = decision.buy_price if decision.action == "buy" else decision.sell_price
        payload = submit_order(
            token,
            app_key,
            app_secret,
            account_no,
            product_code,
            symbol,
            decision.action,
            quantity,
            order_price,
            order_division,
        )
        print("order_response:", json.dumps(payload, ensure_ascii=False, indent=2))
        order_payload = payload
    elif decision.action in {"buy", "sell"}:
        print("DRY_RUN=true: order was not submitted")
        order_payload = {"dry_run": True, "message": "order was not submitted"}
    else:
        print("No order submitted")
        order_payload = {"message": "no order submitted"}

    status = {
        "timestamp": datetime.now(SEOUL_TZ).isoformat(timespec="seconds"),
        "symbol": symbol,
        "dry_run": dry_run,
        "current_price": price,
        "quantity": snapshot.symbol_quantity,
        "cash": snapshot.available_cash,
        "average_price": snapshot.average_price,
        "action": decision.action,
        "buy_price": decision.buy_price,
        "sell_price": decision.sell_price,
        "expected_return": decision.expected_return,
        "loss_probability": decision.loss_probability,
        "reason": decision.reason,
        "order": order_payload,
    }
    logs = PROJECT_DIR / "logs"
    logs.mkdir(exist_ok=True)
    (logs / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (logs / "trader.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(status, ensure_ascii=False) + "\n")
    print(f"status_saved: {logs / 'status.json'}")


if __name__ == "__main__":
    main()
