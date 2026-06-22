"""Small REST client with throttling, timeout handling, and retries."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from auth import TokenManager
from config import Settings


class KISAPIError(RuntimeError):
    pass


class KISClient:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.session = requests.Session()
        self.token_manager = TokenManager(settings, self.session, logger)
        self._last_request_at = 0.0

    def get(self, path: str, tr_id: str, params: dict[str, str]) -> dict[str, Any]:
        return self._request("GET", path, tr_id, params=params)

    def post(self, path: str, tr_id: str, body: dict[str, str]) -> dict[str, Any]:
        return self._request("POST", path, tr_id, json_body=body)

    def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        attempts = self.settings.max_retries + 1
        refreshed_after_401 = False

        for attempt in range(1, attempts + 1):
            self._throttle()
            token = self.token_manager.get_token()
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.settings.app_key,
                "appsecret": self.settings.app_secret,
                "tr_id": tr_id,
                "custtype": "P",
                "content-type": "application/json; charset=utf-8",
            }
            try:
                response = self.session.request(
                    method,
                    f"{self.settings.base_url}{path}",
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=self.settings.request_timeout_seconds,
                )
                self._last_request_at = time.monotonic()

                if response.status_code == 401 and not refreshed_after_401:
                    refreshed_after_401 = True
                    self.token_manager.invalidate()
                    self.logger.warning("Access token rejected; refreshing once")
                    continue

                response.raise_for_status()
                payload = response.json()
                if payload.get("rt_cd") != "0":
                    raise KISAPIError(
                        f"KIS API error {payload.get('msg_cd')}: {payload.get('msg1')}"
                    )
                return payload
            except (requests.Timeout, requests.ConnectionError) as exc:
                self.logger.warning(
                    "API timeout/connection error (attempt %d/%d): %s",
                    attempt,
                    attempts,
                    exc,
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                self.logger.error("HTTP error from KIS API: status=%s", status)
                if status < 500:
                    raise KISAPIError(str(exc)) from exc

            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

        raise KISAPIError(f"KIS API request failed after {attempts} attempts: {method} {path}")

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.settings.request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

