"""KIS access-token issuance and same-day cache reuse."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from config import SEOUL_TZ, Settings


class TokenManager:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.session = session
        self.logger = logger

    def get_token(self) -> str:
        cached = self._read_cache()
        if self._is_reusable(cached):
            self.logger.info("Reusing cached access token for today")
            return str(cached["access_token"])

        self.logger.info("Cached token unavailable or expired; requesting a new token")
        response = self.session.post(
            f"{self.settings.base_url}/oauth2/tokenP",
            headers={"content-type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": self.settings.app_key,
                "appsecret": self.settings.app_secret,
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Token response did not contain access_token: {payload}")

        self._write_cache(
            {
                "access_token": token,
                "issued_date": datetime.now(SEOUL_TZ).date().isoformat(),
                "expires_at": payload.get("access_token_token_expired"),
            }
        )
        self.logger.info("New access token issued and cached")
        return str(token)

    def invalidate(self) -> None:
        try:
            self.settings.token_cache_path.unlink(missing_ok=True)
        except OSError:
            self.logger.warning("Could not remove token cache", exc_info=True)

    def _read_cache(self) -> dict[str, Any]:
        path = self.settings.token_cache_path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.logger.warning("Ignoring unreadable token cache")
            return {}

    def _write_cache(self, payload: dict[str, Any]) -> None:
        path: Path = self.settings.token_cache_path
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _is_reusable(payload: dict[str, Any]) -> bool:
        if not payload.get("access_token"):
            return False
        today = datetime.now(SEOUL_TZ).date().isoformat()
        if payload.get("issued_date") != today:
            return False
        expires_at = payload.get("expires_at")
        if not expires_at:
            return True
        try:
            expiry = datetime.strptime(str(expires_at), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=SEOUL_TZ
            )
        except ValueError:
            return False
        return datetime.now(SEOUL_TZ) < expiry

