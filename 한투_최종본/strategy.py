"""Finance-engineering trading signal logic."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from account import AccountSnapshot
from config import Settings
from finance_math import limit_prices
from simulation import simulate_gbm_paths


@dataclass(frozen=True)
class StrategyDecision:
    action: str
    buy_price: int
    sell_price: int
    expected_return: float
    loss_probability: float
    reason: str


def decide_action(
    *,
    current_price: int,
    snapshot: AccountSnapshot,
    settings: Settings,
) -> StrategyDecision:
    """Decide buy/sell/hold from Brownian scenarios and P&L controls."""
    buy_price, sell_price = limit_prices(current_price, settings.price_offset_krw)

    if settings.strategy_mode == "limit_only":
        return _limit_only_decision(current_price, snapshot, settings, buy_price, sell_price)

    paths = simulate_gbm_paths(
        spot=float(current_price),
        drift=settings.annual_drift,
        volatility=settings.annual_volatility,
        days=settings.simulation_days,
        paths=settings.simulation_paths,
        seed=42,
    )
    terminal_prices = [path[-1] for path in paths]
    expected_terminal = statistics.mean(terminal_prices)
    expected_return = expected_terminal / current_price - 1.0
    loss_probability = sum(price < current_price for price in terminal_prices) / len(terminal_prices)

    if snapshot.symbol_quantity <= 0:
        can_buy = (
            expected_return >= settings.min_expected_return
            and loss_probability <= settings.max_loss_probability
        )
        if can_buy:
            return StrategyDecision(
                action="buy",
                buy_price=buy_price,
                sell_price=sell_price,
                expected_return=expected_return,
                loss_probability=loss_probability,
                reason=(
                    "Brownian expected return is positive enough and downside "
                    "probability is within the risk limit"
                ),
            )
        return StrategyDecision(
            action="hold",
            buy_price=buy_price,
            sell_price=sell_price,
            expected_return=expected_return,
            loss_probability=loss_probability,
            reason="Buy skipped because expected return/risk filter was not satisfied",
        )

    entry = snapshot.average_price or current_price
    realized_return = current_price / entry - 1.0
    if realized_return >= settings.take_profit_pct:
        reason = "Take-profit threshold reached"
        action = "sell"
    elif realized_return <= -settings.stop_loss_pct:
        reason = "Stop-loss threshold reached"
        action = "sell"
    elif expected_return < 0:
        reason = "Brownian scenario expected return turned negative"
        action = "sell"
    else:
        reason = "Holding because risk and return filters do not require selling"
        action = "hold"

    return StrategyDecision(
        action=action,
        buy_price=buy_price,
        sell_price=sell_price,
        expected_return=expected_return,
        loss_probability=loss_probability,
        reason=reason,
    )


def _limit_only_decision(
    current_price: int,
    snapshot: AccountSnapshot,
    settings: Settings,
    buy_price: int,
    sell_price: int,
) -> StrategyDecision:
    action = "sell" if snapshot.symbol_quantity >= settings.order_quantity else "buy"
    return StrategyDecision(
        action=action,
        buy_price=buy_price,
        sell_price=sell_price,
        expected_return=0.0,
        loss_probability=0.0,
        reason="Legacy limit-only rule",
    )
