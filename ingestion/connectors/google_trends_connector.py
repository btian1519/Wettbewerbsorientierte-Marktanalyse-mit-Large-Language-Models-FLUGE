"""Google Trends connector — demand proxy (one signal among several).

Uses ``pytrends`` when installed (no API key needed). Kept behind ``is_configured``
so the app runs fine without it; the demand engine treats the output as *one*
proxy, never as demand itself.
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorError, ConnectorStatus
from ingestion.connectors.records import RawTrendPoint
from shared.sources import DataSource

try:  # optional dependency
    from pytrends.request import TrendReq  # type: ignore

    _PYTRENDS = True
except Exception:  # pragma: no cover
    TrendReq = None  # type: ignore
    _PYTRENDS = False


class GoogleTrendsConnector(BaseConnector):
    source = DataSource.GOOGLE_TRENDS
    base_url = "https://trends.google.com"

    def is_configured(self) -> bool:
        return _PYTRENDS

    def fetch_interest(self, keyword: str, timeframe: str = "today 3-m") -> list[RawTrendPoint]:
        """Weekly search-interest series for a single keyword."""
        if not _PYTRENDS:
            raise ConnectorError(
                "google_trends: pytrends is not installed. `pip install pytrends` to enable."
            )
        try:
            pt = TrendReq(hl="en-US", tz=0)
            pt.build_payload([keyword], timeframe=timeframe)
            df = pt.interest_over_time()
        except Exception as exc:  # pytrends raises many ad-hoc errors
            raise ConnectorError(f"google_trends: {exc}") from exc
        if df is None or df.empty or keyword not in df:
            return []
        out: list[RawTrendPoint] = []
        for ts, value in df[keyword].items():
            out.append(
                RawTrendPoint(
                    keyword=keyword,
                    week=f"{ts.isocalendar().year}-W{ts.isocalendar().week:02d}",
                    value=float(value),
                    timeframe=timeframe,
                    source=self.source.value,
                )
            )
        return out

    def probe(self) -> ConnectorStatus:
        return self.status(reachable=_PYTRENDS or None)
