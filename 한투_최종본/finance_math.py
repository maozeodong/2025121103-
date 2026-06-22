"""Small finance-engineering utilities used by the final project.

The functions in this file are intentionally dependency-free so they can run in
Codespaces, Colab, or a plain Python environment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class BlackScholesResult:
    call: float
    put: float
    d1: float
    d2: float
    delta_call: float
    delta_put: float


def black_scholes_price(
    spot: float,
    strike: float,
    rate: float,
    volatility: float,
    maturity: float,
) -> BlackScholesResult:
    """Price a European call/put under the Black-Scholes formula."""
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if volatility <= 0 or maturity <= 0:
        raise ValueError("volatility and maturity must be positive")

    sqrt_t = math.sqrt(maturity)
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility**2) * maturity) / (
        volatility * sqrt_t
    )
    d2 = d1 - volatility * sqrt_t
    discount = math.exp(-rate * maturity)
    call = spot * normal_cdf(d1) - strike * discount * normal_cdf(d2)
    put = strike * discount * normal_cdf(-d2) - spot * normal_cdf(-d1)
    return BlackScholesResult(
        call=call,
        put=put,
        d1=d1,
        d2=d2,
        delta_call=normal_cdf(d1),
        delta_put=normal_cdf(d1) - 1.0,
    )


def put_call_parity_gap(
    call_price: float,
    put_price: float,
    spot: float,
    strike: float,
    rate: float,
    maturity: float,
) -> float:
    """Return C - P - (S - K exp(-rT)); near zero means parity holds."""
    return call_price - put_price - (spot - strike * math.exp(-rate * maturity))


def stock_pnl(
    current_price: float,
    entry_price: float,
    quantity: int,
    transaction_cost: float = 0.0,
) -> float:
    """Mark-to-market P&L for a stock position."""
    return quantity * (current_price - entry_price) - transaction_cost


def limit_prices(current_price: int, offset_krw: int) -> tuple[int, int]:
    """Return conservative buy/sell limit prices around the current price."""
    return max(current_price - offset_krw, 1), current_price + offset_krw
