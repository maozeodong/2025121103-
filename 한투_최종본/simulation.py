"""Brownian-motion price simulation and scenario analysis."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScenarioRow:
    scenario: str
    price: float
    pnl: float


def simulate_gbm_paths(
    *,
    spot: float,
    drift: float = 0.0,
    volatility: float = 0.2,
    days: int = 30,
    paths: int = 5,
    seed: int = 42,
) -> list[list[float]]:
    """Simulate geometric Brownian motion paths for a stock price."""
    if spot <= 0:
        raise ValueError("spot must be positive")
    if days <= 0 or paths <= 0:
        raise ValueError("days and paths must be positive")

    rng = random.Random(seed)
    dt = 1.0 / 252.0
    result: list[list[float]] = []
    for _ in range(paths):
        prices = [float(spot)]
        price = float(spot)
        for _day in range(days):
            z = rng.gauss(0.0, 1.0)
            price *= math.exp((drift - 0.5 * volatility**2) * dt + volatility * math.sqrt(dt) * z)
            prices.append(price)
        result.append(prices)
    return result


def pnl_scenarios(
    *,
    current_price: float,
    entry_price: float,
    quantity: int,
    transaction_cost: float = 0.0,
) -> list[ScenarioRow]:
    """Simple +/- price-shock P&L scenarios."""
    shocks = [
        ("down_3pct", -0.03),
        ("down_1pct", -0.01),
        ("unchanged", 0.0),
        ("up_1pct", 0.01),
        ("up_3pct", 0.03),
    ]
    rows = []
    for name, shock in shocks:
        price = current_price * (1.0 + shock)
        pnl = quantity * (price - entry_price) - transaction_cost
        rows.append(ScenarioRow(name, price, pnl))
    return rows


def write_paths_csv(paths: list[list[float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["day", *[f"path_{i + 1}" for i in range(len(paths))]])
        for day in range(len(paths[0])):
            writer.writerow([day, *[round(path[day], 2) for path in paths]])


def write_scenarios_csv(rows: list[ScenarioRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "price", "pnl"])
        for row in rows:
            writer.writerow([row.scenario, round(row.price, 2), round(row.pnl, 2)])
