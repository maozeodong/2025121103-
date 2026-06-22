"""Generate a finance-engineering report around the KIS trading project.

This script can run without real KIS credentials. It uses a supplied current
price to produce CSV/Markdown artifacts that connect the API project to the
course topics: P&L, Brownian motion, Black-Scholes, and put-call parity.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from finance_math import black_scholes_price, limit_prices, put_call_parity_gap, stock_pnl
from simulation import pnl_scenarios, simulate_gbm_paths, write_paths_csv, write_scenarios_csv


def build_report(
    *,
    symbol: str,
    current_price: int,
    quantity: int,
    offset_krw: int,
    output_dir: Path,
    entry_price: int | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    entry = entry_price if entry_price is not None else current_price
    buy_price, sell_price = limit_prices(current_price, offset_krw)

    scenarios = pnl_scenarios(
        current_price=current_price,
        entry_price=entry,
        quantity=quantity,
        transaction_cost=0.0,
    )
    paths = simulate_gbm_paths(spot=current_price, volatility=0.2, days=30, paths=5)

    scenario_csv = output_dir / "pnl_scenarios.csv"
    paths_csv = output_dir / "brownian_paths.csv"
    write_scenarios_csv(scenarios, scenario_csv)
    write_paths_csv(paths, paths_csv)

    strike = round(current_price / 1000) * 1000
    maturity = 30 / 252
    bs = black_scholes_price(
        spot=float(current_price),
        strike=float(strike),
        rate=0.03,
        volatility=0.2,
        maturity=maturity,
    )
    parity_gap = put_call_parity_gap(
        call_price=bs.call,
        put_price=bs.put,
        spot=float(current_price),
        strike=float(strike),
        rate=0.03,
        maturity=maturity,
    )
    current_pnl = stock_pnl(current_price, entry, quantity)

    report = output_dir / "final_finance_report.md"
    report.write_text(
        f"""# KIS + Finance Engineering Report

## 1. Market Data

- Symbol: `{symbol}`
- Current price: `{current_price:,}` KRW
- Quantity: `{quantity}`
- Reference entry price: `{entry:,}` KRW
- Current mark-to-market P&L: `{current_pnl:,.2f}` KRW

## 2. Trading Rule

The project uses a conservative limit-order rule around the current price.

```text
buy_limit  = current_price - PRICE_OFFSET_KRW = {buy_price:,}
sell_limit = current_price + PRICE_OFFSET_KRW = {sell_price:,}
```

This is not claimed to be an alpha-generating strategy. It is a safe API
prototype for checking token issuance, price inquiry, account inquiry, and mock
order submission.

## 3. P&L Scenario Analysis

The scenario file `{scenario_csv.name}` evaluates P&L under simple price shocks.
This connects the API project to the P&L framework from the deep-hedging part of
the course.

## 4. Brownian-Motion Simulation

The file `{paths_csv.name}` contains geometric Brownian motion paths simulated
from the current price. This reflects the course idea that an asset price path
can be modeled as a stochastic process.

## 5. Black-Scholes and Put-Call Parity Check

Using a 30-trading-day maturity, volatility 20%, and risk-free rate 3%:

- Strike: `{strike:,}`
- Black-Scholes call: `{bs.call:,.4f}`
- Black-Scholes put: `{bs.put:,.4f}`
- Call delta: `{bs.delta_call:.4f}`
- Put delta: `{bs.delta_put:.4f}`
- Put-call parity gap: `{parity_gap:.8f}`

The parity gap is near zero because the call and put prices are generated from
the same Black-Scholes model. In a real extension, option quotes from KIS or
another data source could be used to test whether market prices satisfy parity.

## 6. Course Connection

This report connects the final project to the course sequence:

- PyTorch and model training: TinyGPT implementation
- Brownian motion: stochastic stock-price scenarios
- P&L: mark-to-market and price-shock analysis
- Deep hedging: position-aware trading loop and rebalancing intuition
- Postman/KIS: REST API token, current price, balance, and order endpoints
- Put-call parity: option-pricing consistency check
""",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate finance-engineering final report artifacts")
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--current-price", type=int, default=73500)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--offset-krw", type=int, default=1000)
    parser.add_argument("--entry-price", type=int)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    report = build_report(
        symbol=args.symbol,
        current_price=args.current_price,
        quantity=args.quantity,
        offset_krw=args.offset_krw,
        entry_price=args.entry_price,
        output_dir=Path(args.output_dir),
    )
    print(f"generated {report}")


if __name__ == "__main__":
    main()
