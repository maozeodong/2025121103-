"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

def load_dotenv(path: Path) -> bool:
    """Load a simple KEY=VALUE .env file without an external dependency."""
    if not path.exists():
        return False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
    return True

PROJECT_DIR = Path(__file__).resolve().parent
SEOUL_TZ = ZoneInfo("Asia/Seoul")


def _get_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _get_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return raw == "true"


def _split_account(account: str) -> tuple[str, str]:
    normalized = account.replace("-", "").strip()
    if len(normalized) != 10 or not normalized.isdigit():
        raise ValueError("GH_ACCOUNT must contain a 10-digit account number, e.g. 12345678-01")
    return normalized[:8], normalized[8:]


@dataclass(frozen=True)
class Settings:
    app_key: str
    app_secret: str
    account_number: str
    account_product_code: str
    base_url: str = "https://openapivts.koreainvestment.com:29443"
    symbol: str = "005930"
    market_code: str = "J"
    exchange_code: str = "KRX"
    price_offset_krw: int = 1_000
    order_quantity: int = 1
    poll_interval_seconds: int = 300
    order_verify_delay_seconds: int = 10
    request_interval_seconds: float = 0.5
    request_timeout_seconds: float = 10.0
    max_retries: int = 2
    dry_run: bool = True
    trading_window_mode: str = "regular"
    order_division: str = "00"
    strategy_mode: str = "finance"
    annual_drift: float = 0.05
    annual_volatility: float = 0.20
    simulation_days: int = 20
    simulation_paths: int = 500
    min_expected_return: float = 0.001
    max_loss_probability: float = 0.48
    take_profit_pct: float = 0.01
    stop_loss_pct: float = 0.01
    trading_start: time = time(9, 10)
    trading_end: time = time(15, 30)
    token_cache_path: Path = PROJECT_DIR / "token_cache.json"
    log_dir: Path = PROJECT_DIR / "logs"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_DIR / ".env")
        required = ("GH_ACCOUNT", "GH_APPKEY", "GH_APPSECRET")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        account_number, product_code = _split_account(os.environ["GH_ACCOUNT"])
        return cls(
            app_key=os.environ["GH_APPKEY"].strip(),
            app_secret=os.environ["GH_APPSECRET"].strip(),
            account_number=account_number,
            account_product_code=product_code,
            symbol=os.getenv("SYMBOL", "005930").strip(),
            market_code=os.getenv("MARKET_CODE", "J").strip(),
            exchange_code=os.getenv("EXCHANGE_CODE", "KRX").strip(),
            price_offset_krw=_get_int("PRICE_OFFSET_KRW", 1_000, 1),
            order_quantity=_get_int("ORDER_QUANTITY", 1, 1),
            poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 300, 30),
            order_verify_delay_seconds=_get_int("ORDER_VERIFY_DELAY_SECONDS", 10, 1),
            request_interval_seconds=_get_float("REQUEST_INTERVAL_SECONDS", 0.5, 0.1),
            request_timeout_seconds=_get_float("REQUEST_TIMEOUT_SECONDS", 10.0, 1.0),
            max_retries=_get_int("MAX_RETRIES", 2, 0),
            dry_run=_get_bool("DRY_RUN", True),
            trading_window_mode=os.getenv("TRADING_WINDOW_MODE", "regular").strip().lower(),
            order_division=os.getenv("ORDER_DIVISION", "00").strip(),
            strategy_mode=os.getenv("STRATEGY_MODE", "finance").strip().lower(),
            annual_drift=_get_float("ANNUAL_DRIFT", 0.05, -1.0),
            annual_volatility=_get_float("ANNUAL_VOLATILITY", 0.20, 0.0001),
            simulation_days=_get_int("SIMULATION_DAYS", 20, 1),
            simulation_paths=_get_int("SIMULATION_PATHS", 500, 10),
            min_expected_return=_get_float("MIN_EXPECTED_RETURN", 0.001, -1.0),
            max_loss_probability=_get_float("MAX_LOSS_PROBABILITY", 0.48, 0.0),
            take_profit_pct=_get_float("TAKE_PROFIT_PCT", 0.01, 0.0),
            stop_loss_pct=_get_float("STOP_LOSS_PCT", 0.01, 0.0),
        )
