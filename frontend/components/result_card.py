"""Result card: teal header (rank / route / suggestion / benefit) + details.

Per the brief the details panel intentionally shows the *count* of active
airlines on the route but never names any carrier ("keine Fluglinie
darstellen"). Airport details only surface fields that actually exist in
AIRPORTS (IATA, airport name and region — the source file has no city column and
its country column is empty). In overcapacity mode Benefit and the gap figure are
displayed as absolute values via ``RouteResult.display_*``.
"""

from __future__ import annotations

import html

import streamlit as st

from backend.dto import RouteResult
from shared.constants import Task
from shared.utils import format_eur, format_pax


def _suggestion(task_value: str) -> str:
    return "Open new route" if task_value == Task.OPPORTUNITIES.value else "Cut capacity"


def _card_header_html(r: RouteResult, task_value: str) -> str:
    return f"""
<div class="fs-card">
  <div class="fs-rank">{r.rank}</div>
  <div class="fs-route">{r.origin_iata} &ndash; {r.dest_iata}</div>
  <div class="fs-spacer"></div>
  <div class="fs-chip"><span class="lbl">SUGGESTION</span><span class="val">{_suggestion(task_value)}</span></div>
  <div class="fs-chip"><span class="lbl">BENEFIT</span><span class="val">{format_eur(r.display_benefit)}/wk</span></div>
  <div class="fs-chip"><span class="lbl">{r.gap_label.upper()}</span><span class="val">{format_pax(r.display_delta)} pax/wk</span></div>
</div>
"""


def _airport_block(
    name: str | None, iata: str, city: str | None, country: str | None, continent: str
) -> str:
    """Stacked airport details in the required order, omitting missing values.

        Airport (IATA)
        City, Country
        Region

    No placeholders are ever shown — a missing field simply drops its line.
    """
    lines: list[str] = []
    header = f"{html.escape(name)} ({iata})" if name else iata
    lines.append(f'<div class="apt-name">{header}</div>')
    loc = ", ".join(html.escape(p) for p in (city, country) if p)
    if loc:
        lines.append(f'<div class="apt-loc">{loc}</div>')
    lines.append(f'<div class="apt-region">{html.escape(continent)}</div>')
    return f'<div class="fs-airport">{"".join(lines)}</div>'


def _details_html(r: RouteResult) -> str:
    share_pct = f"{r.selected_airline_share * 100:.1f}%"
    return f"""
<div class="fs-detail-grid">
  <div class="fs-detail-h">Origin</div><div class="fs-detail-h">Destination</div>
  <div style="grid-column:1">{_airport_block(r.origin_name, r.origin_iata, r.origin_city, r.origin_country, r.origin_continent)}</div>
  <div style="grid-column:2">{_airport_block(r.dest_name, r.dest_iata, r.dest_city, r.dest_country, r.dest_continent)}</div>
</div>
<hr style="margin:.6rem 0;border:none;border-top:1px solid #e2e6e8;">
<div class="fs-detail-grid">
  <div class="k">Distance</div><div class="v">{r.distance_km:,.0f} km</div>
  <div class="k">Average price</div><div class="v">&euro;{r.avg_price_eur:,.0f}</div>
  <div class="k">Total demand</div><div class="v">{format_pax(r.demand)} pax/wk</div>
  <div class="k">Total supply</div><div class="v">{format_pax(r.total_supply)} seats/wk</div>
  <div class="k">Market share (selected airline)</div><div class="v">{share_pct}</div>
  <div class="k">Active airlines on route</div><div class="v">{r.num_airlines}</div>
  <div class="k">{r.gap_label}</div><div class="v">{format_pax(r.display_delta)} pax/wk</div>
  <div class="k">Benefit</div><div class="v">{format_eur(r.display_benefit)}/wk</div>
</div>
"""


def render_result_card(r: RouteResult, task_value: str) -> None:
    st.markdown(_card_header_html(r, task_value), unsafe_allow_html=True)
    with st.expander("Show Details"):
        st.markdown(_details_html(r), unsafe_allow_html=True)
