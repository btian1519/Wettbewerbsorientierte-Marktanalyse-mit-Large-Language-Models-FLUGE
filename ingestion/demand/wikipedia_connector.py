"""Wikipedia pageviews demand connector — additional travel-interest proxy.

Uses the public Wikimedia REST pageviews API (no key). For a route it sums recent
monthly pageviews of the origin and destination city articles as a travel-interest
signal. All resilience comes from :class:`BaseConnector`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ingestion.connectors.base import BaseConnector
from ingestion.demand.records import RawSignal, RouteContext
from shared.sources import DataSource


class WikipediaDemandConnector(BaseConnector):
    source = DataSource.WIKIPEDIA
    signal_type = "wikipedia_views"
    base_url = "https://wikimedia.org/api/rest_v1"
    # Fail fast on the very first request: one HTTP call, no retries. Combined with
    # the demand pipeline's first-strike pause, this means a single request at most
    # before the source flips to the provider-limited state (no minutes-long sync).
    max_attempts = 1
    # Present provider hiccups (429/404/timeout) as a single clean "provider limited"
    # state upstream, so the raw HTTP errors never reach the operator log / the
    # investor-facing "Recent System Messages" panel.
    quiet_failures = True

    def available(self) -> bool:
        return True

    def _auth_headers(self) -> dict[str, str]:
        # Wikimedia requires a descriptive User-Agent.
        return {"User-Agent": "FlightScopeAI/1.0 (demand-platform)"}

    def fetch(self, ctx: RouteContext, week: str) -> list[RawSignal]:
        cities = [c for c in (ctx.origin_city, ctx.dest_city) if c]
        if not cities:
            return []
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=70)
        s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

        total = 0.0
        for city in cities:
            article = quote(city.replace(" ", "_"), safe="")
            path = (
                f"metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/"
                f"{article}/monthly/{s}/{e}"
            )
            # Any failure (HTTP 404/429, timeout, connection error, …) propagates:
            # DemandService's unified handler pauses this source on the first strike,
            # exactly like AirLabs. Nothing is swallowed here anymore, so a provider
            # problem can never be hidden and re-hammered once per O-D pair.
            payload = self._get(path)
            items = payload.get("items") if isinstance(payload, dict) else None
            if items:
                total += float(items[-1].get("views", 0))
        if total <= 0:
            return []
        return [
            RawSignal(
                origin_airport=ctx.origin_iata, destination_airport=ctx.dest_iata,
                signal_type=self.signal_type, signal_value=total,
                search_term="+".join(cities), source=self.source.value, week=week,
            )
        ]

    def probe(self):
        try:
            self._get("metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/"
                      "London/monthly/20250101/20250201")
            return self.status(reachable=True)
        except Exception:  # noqa: BLE001
            return self.status(reachable=False)
