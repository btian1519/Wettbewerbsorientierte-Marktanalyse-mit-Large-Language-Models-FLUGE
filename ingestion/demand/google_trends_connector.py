"""Google Trends demand connector — short-term search interest (a proxy only).

Builds several search terms per route and returns their interest as raw signals.
Uses ``pytrends`` when installed; degrades cleanly (``available()`` False) when it
is not, so the platform runs without it.
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorError
from ingestion.demand.records import RawSignal, RouteContext
from shared.sources import DataSource

try:  # optional dependency
    from pytrends.request import TrendReq  # type: ignore

    _PYTRENDS = True
except Exception:  # pragma: no cover
    TrendReq = None  # type: ignore
    _PYTRENDS = False


def build_search_terms(ctx: RouteContext) -> list[str]:
    """Multiple phrasings per route (city names when known, IATA fallback)."""
    o_city = ctx.origin_city or ctx.origin_iata
    d_city = ctx.dest_city or ctx.dest_iata
    return [
        f"{o_city} {d_city}",
        f"Flights {o_city} {d_city}",
        f"{ctx.origin_iata} {ctx.dest_iata}",
    ]


class GoogleTrendsDemandConnector(BaseConnector):
    source = DataSource.GOOGLE_TRENDS
    signal_type = "google_trends"
    base_url = "https://trends.google.com"

    def available(self) -> bool:
        return _PYTRENDS

    def fetch(self, ctx: RouteContext, week: str) -> list[RawSignal]:
        if not _PYTRENDS:
            raise ConnectorError("google_trends: pytrends not installed")
        terms = build_search_terms(ctx)
        out: list[RawSignal] = []
        try:
            pt = TrendReq(hl="en-US", tz=0)
            for term in terms:
                pt.build_payload([term], timeframe="today 3-m")
                df = pt.interest_over_time()
                if df is None or df.empty or term not in df:
                    continue
                value = float(df[term].tail(4).mean())  # recent 4 weeks
                out.append(RawSignal(
                    origin_airport=ctx.origin_iata, destination_airport=ctx.dest_iata,
                    signal_type=self.signal_type, signal_value=value, search_term=term,
                    source=self.source.value, week=week,
                ))
        except Exception as exc:  # pytrends raises ad-hoc errors
            raise ConnectorError(f"google_trends: {exc}") from exc
        return out
