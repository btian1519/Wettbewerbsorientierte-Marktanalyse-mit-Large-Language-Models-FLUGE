"""Amadeus connector — future price / availability / demand indicators.

Docs: https://developers.amadeus.com/ . OAuth2 client-credentials flow. Prepared:
the token handshake and request scaffolding are implemented; endpoint-specific
parsing activates once a self-service key is supplied via the environment.
"""

from __future__ import annotations

from typing import Any

import requests

from ingestion.connectors.base import BaseConnector, ConnectorError, ConnectorStatus
from shared.sources import DataSource


class AmadeusConnector(BaseConnector):
    source = DataSource.AMADEUS
    base_url = "https://test.api.amadeus.com"
    _token_path = "/v1/security/oauth2/token"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token: str | None = None

    def is_configured(self) -> bool:
        return bool(self._settings.amadeus_client_id and self._settings.amadeus_client_secret)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _ensure_token(self) -> None:
        if self._token or not self.is_configured():
            if not self.is_configured():
                raise ConnectorError("amadeus: not configured")
            return
        try:
            resp = self._session.post(
                f"{self.base_url}{self._token_path}",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._settings.amadeus_client_id,
                    "client_secret": self._settings.amadeus_client_secret,
                },
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            self._token = resp.json().get("access_token")
        except requests.RequestException as exc:
            raise ConnectorError(f"amadeus: token request failed: {exc}") from exc

    def fetch_flight_offers(self, origin: str, dest: str, date: str) -> list[dict[str, Any]]:
        """Prepared: obtain an OAuth token, then query flight offers/prices."""
        self._ensure_token()
        raise NotImplementedError(
            "AmadeusConnector.fetch_flight_offers is a prepared interface; enable by "
            "supplying AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET and parsing the offers payload."
        )

    def probe(self) -> ConnectorStatus:
        try:
            self._ensure_token()
            return self.status(reachable=self._token is not None)
        except ConnectorError:
            return self.status(reachable=False)
