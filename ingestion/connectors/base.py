"""Base class + shared plumbing for all API connectors.

Every connector inherits: authentication, HTTP request handling, error handling,
structured logging, rate limiting, retry with backoff (tenacity) and a health
check. Concrete connectors only declare their base URL, how to authenticate, and
how to parse responses into :mod:`ingestion.connectors.records`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.config import Settings, get_settings
from shared.logging_config import get_logger
from shared.sources import DataSource


class ConnectorError(RuntimeError):
    """Base error for connector failures (network, HTTP, parsing)."""


class AuthError(ConnectorError):
    """Missing or rejected credentials."""


class RateLimitError(ConnectorError):
    """The remote API signalled a rate limit (HTTP 429)."""


class QuotaExceededError(ConnectorError):
    """The API's request quota (e.g. monthly free-tier limit) is exhausted.

    Not retryable and not a per-request failure — the whole sync should stop
    immediately rather than hammering every airport with the same error.
    """


class TransientError(ConnectorError):
    """A retryable network/server error (timeout, 5xx)."""


@dataclass(frozen=True)
class ConnectorStatus:
    name: str
    configured: bool
    reachable: bool | None
    last_error: str | None
    last_checked: datetime | None

    @property
    def label(self) -> str:
        if not self.configured:
            return "not configured"
        if self.reachable is None:
            return "unknown"
        return "connected" if self.reachable else "disconnected"


class BaseConnector:
    """Resilient HTTP client foundation for a single data source."""

    source: DataSource = DataSource.COMPUTED
    base_url: str = ""
    #: Minimum seconds between requests (simple client-side rate limiting).
    min_interval_s: float = 0.25
    timeout_s: float = 15.0
    max_attempts: int = 3
    #: Consecutive failed requests before the per-connector circuit opens and every
    #: further request fails fast — no network call and no repeated error log. This
    #: stops error storms even when the caller swallows individual failures. 0
    #: disables the breaker (default), so connectors opt in explicitly.
    circuit_breaker_threshold: int = 0

    def __init__(self, settings: Settings | None = None, session: requests.Session | None = None) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()
        self._log = get_logger(f"ingestion.connector.{self.source.value}")
        self._last_request_ts = 0.0
        self._last_error: str | None = None
        self._last_checked: datetime | None = None
        self._consecutive_failures = 0
        self._circuit_open = False

    def reset_circuit(self) -> None:
        """Close the circuit and clear the failure streak (call before a fresh run)."""
        self._consecutive_failures = 0
        self._circuit_open = False

    def is_circuit_open(self) -> bool:
        return self._circuit_open

    # ------------------------------------------------------------------ #
    # Auth (override in subclasses that need it)
    # ------------------------------------------------------------------ #
    def is_configured(self) -> bool:
        """Whether the connector has everything it needs (keys etc.)."""
        return True

    def _auth_params(self) -> dict[str, Any]:
        return {}

    def _auth_headers(self) -> dict[str, str]:
        return {}

    # ------------------------------------------------------------------ #
    # Request handling
    # ------------------------------------------------------------------ #
    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_request_ts = time.monotonic()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET with rate limiting, retry/backoff, and typed error mapping."""
        if self._circuit_open:
            # Fail fast: the breaker already reported the outage when it opened, so
            # skip the network and stay quiet to avoid an error-log storm.
            raise ConnectorError(f"{self.source.value}: circuit open (skipping after repeated failures)")
        if not self.is_configured():
            raise AuthError(f"{self.source.value}: connector is not configured (missing credentials)")

        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if path else self.base_url
        merged = {**(params or {}), **self._auth_params()}

        @retry(
            retry=retry_if_exception_type((TransientError, RateLimitError)),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            stop=stop_after_attempt(self.max_attempts),
            reraise=True,
        )
        def _do() -> Any:
            self._rate_limit()
            try:
                resp = self._session.get(
                    url, params=merged, headers=self._auth_headers(), timeout=self.timeout_s
                )
            except requests.RequestException as exc:
                self._log.warning("Request error to %s: %s", url, exc)
                raise TransientError(str(exc)) from exc

            if resp.status_code == 429:
                self._log.warning("Rate limited by %s (429)", self.source.value)
                raise RateLimitError(f"{self.source.value}: HTTP 429")
            if resp.status_code in (401, 403):
                raise AuthError(f"{self.source.value}: HTTP {resp.status_code}")
            if resp.status_code >= 500:
                raise TransientError(f"{self.source.value}: HTTP {resp.status_code}")
            if resp.status_code >= 400:
                raise ConnectorError(f"{self.source.value}: HTTP {resp.status_code} — {resp.text[:200]}")

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(f"{self.source.value}: invalid JSON response") from exc

        try:
            data = _do()
            self._last_error = None
            self._consecutive_failures = 0  # a clean call closes any streak
            return data
        except ConnectorError as exc:
            self._last_error = str(exc)
            self._consecutive_failures += 1
            if self.circuit_breaker_threshold and self._consecutive_failures >= self.circuit_breaker_threshold:
                if not self._circuit_open:
                    self._circuit_open = True
                    self._log.error(
                        "Connector %s failing repeatedly — opening circuit after %d failures; "
                        "further requests are skipped until reset.",
                        self.source.value, self._consecutive_failures,
                    )
                # Circuit just opened (or already open): suppress the per-request log.
            else:
                self._log.error("Connector %s failed: %s", self.source.value, exc)
            raise

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #
    def health_check(self) -> ConnectorStatus:
        """Lightweight reachability probe. Subclasses may override with a real
        ping; the default reports configuration state without a network call."""
        self._last_checked = datetime.now(timezone.utc)
        return ConnectorStatus(
            name=self.source.value,
            configured=self.is_configured(),
            reachable=None,
            last_error=self._last_error,
            last_checked=self._last_checked,
        )

    def status(self, reachable: bool | None = None) -> ConnectorStatus:
        return ConnectorStatus(
            name=self.source.value,
            configured=self.is_configured(),
            reachable=reachable,
            last_error=self._last_error,
            last_checked=self._last_checked,
        )
