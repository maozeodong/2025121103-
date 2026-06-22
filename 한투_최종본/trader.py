"""Polling-based trading loop with conservative request usage."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from account import AccountSnapshot, get_account_snapshot
from api_client import KISAPIError, KISClient
from config import SEOUL_TZ, Settings
from market_data import get_current_price
from orders import OrderSide, place_limit_order
from strategy import decide_action


@dataclass
class PendingOrder:
    side: OrderSide
    quantity_before: int


class Trader:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.client = KISClient(settings, logger)
        self.pending: dict[OrderSide, PendingOrder] = {}

    def run(self) -> None:
        self.logger.info(
            "Trader started: symbol=%s, window_mode=%s, window=%s-%s KST, dry_run=%s",
            self.settings.symbol,
            self.settings.trading_window_mode,
            self.settings.trading_start,
            self.settings.trading_end,
            self.settings.dry_run,
        )

        while True:
            now = datetime.now(SEOUL_TZ)
            if self.settings.trading_window_mode == "always":
                self.logger.info("Trading window bypassed by TRADING_WINDOW_MODE=always")
            elif now.time() >= self.settings.trading_end:
                self.logger.info("Trading window ended; stopping automatically")
                return
            elif now.time() < self.settings.trading_start:
                wait_seconds = self._seconds_until_start(now)
                self.logger.info("Outside trading window; waiting %d seconds", wait_seconds)
                time.sleep(min(wait_seconds, 60))
                continue

            self.logger.info("Trading window active")
            try:
                self._run_cycle()
            except KISAPIError:
                self.logger.exception("Trading cycle failed due to API error")
            except Exception:
                self.logger.exception("Unexpected trading cycle error")

            time.sleep(self.settings.poll_interval_seconds)

    def _run_cycle(self) -> None:
        price = get_current_price(self.client, self.settings)
        self.logger.info("Current price: %s KRW", f"{price:,}")

        before = get_account_snapshot(self.client, self.settings)
        self.logger.info(
            "Holdings before order: quantity=%d, available_cash=%s KRW",
            before.symbol_quantity,
            f"{before.available_cash:,}",
        )
        self._clear_filled_pending(before)

        decision = decide_action(current_price=price, snapshot=before, settings=self.settings)
        self.logger.info(
            "Strategy decision: action=%s, expected_return=%.4f%%, loss_probability=%.2f%%, reason=%s",
            decision.action,
            decision.expected_return * 100,
            decision.loss_probability * 100,
            decision.reason,
        )
        buy_price = decision.buy_price
        sell_price = decision.sell_price
        snapshot = before

        if decision.action == "buy" and "buy" not in self.pending:
            if snapshot.available_cash >= buy_price * self.settings.order_quantity:
                snapshot = self._submit_and_verify("buy", buy_price, snapshot)
            else:
                self.logger.warning("Skipping buy: insufficient available cash")
        elif "buy" in self.pending:
            self.logger.info("Skipping duplicate buy while prior buy appears pending")
        else:
            self.logger.info("Skipping buy: strategy action is %s", decision.action)

        if decision.action == "sell" and "sell" not in self.pending:
            if snapshot.symbol_quantity >= self.settings.order_quantity:
                self._submit_and_verify("sell", sell_price, snapshot)
            else:
                self.logger.info("Skipping sell: no sufficient confirmed holdings")
        elif "sell" in self.pending:
            self.logger.info("Skipping duplicate sell while prior sell appears pending")
        else:
            self.logger.info("Skipping sell: strategy action is %s", decision.action)

    def _submit_and_verify(
        self,
        side: OrderSide,
        price: int,
        before: AccountSnapshot,
    ) -> AccountSnapshot:
        self.logger.info(
            "%s order request: symbol=%s, quantity=%d, limit_price=%s KRW",
            side.upper(),
            self.settings.symbol,
            self.settings.order_quantity,
            f"{price:,}",
        )
        if self.settings.dry_run:
            self.logger.info("DRY_RUN enabled; order was not sent")
            return before

        self.pending[side] = PendingOrder(side, before.symbol_quantity)
        result = place_limit_order(self.client, self.settings, side, price)
        self.logger.info(
            "%s order accepted: order_number=%s, message=%s",
            side.upper(),
            result.order_number or "(not returned)",
            result.message,
        )
        time.sleep(self.settings.order_verify_delay_seconds)

        after = get_account_snapshot(self.client, self.settings)
        self.logger.info(
            "Holdings after %s order: quantity=%d, available_cash=%s KRW",
            side,
            after.symbol_quantity,
            f"{after.available_cash:,}",
        )
        executed = (
            after.symbol_quantity > before.symbol_quantity
            if side == "buy"
            else after.symbol_quantity < before.symbol_quantity
        )
        if executed:
            self.pending.pop(side, None)
            self.logger.info("%s execution appears to have occurred", side.upper())
        else:
            self.logger.info(
                "%s execution not yet reflected; suppressing duplicate orders", side.upper()
            )
        return after

    def _clear_filled_pending(self, snapshot: AccountSnapshot) -> None:
        buy = self.pending.get("buy")
        if buy and snapshot.symbol_quantity > buy.quantity_before:
            self.pending.pop("buy", None)
            self.logger.info("Previously pending BUY now appears executed")

        sell = self.pending.get("sell")
        if sell and snapshot.symbol_quantity < sell.quantity_before:
            self.pending.pop("sell", None)
            self.logger.info("Previously pending SELL now appears executed")

    def _seconds_until_start(self, now: datetime) -> int:
        start = datetime.combine(now.date(), self.settings.trading_start, SEOUL_TZ)
        if start <= now:
            start += timedelta(days=1)
        return max(1, int((start - now).total_seconds()))
