"""Result card: teal header (rank / route / suggestion / benefit) + details.

Per the brief the details panel intentionally shows the *count* of active
airlines on the route but never names any carrier ("keine Fluglinie
darstellen").
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
  <div class="fs-chip"><span class="lbl">BENEFIT</span><span class="val">{format_eur(r.benefit_eur)}</span></div>
  <div class="fs-chip"><span class="lbl">{r.gap_label.upper()}</span><span class="val">{format_pax(r.delta_pax)} pax</span></div>
</div>
"""


def _airport_line(name: str | None, iata: str, country: str | None, continent: str) -> str:
    label = html.escape(name) if name else iata
    loc = html.escape(country) if country else continent
    return f"{label} ({iata}) &middot; {loc}"


def _details_html(r: RouteResult) -> str:
    share_pct = f"{r.selected_airline_share * 100:.1f}%"
    return f"""
<div class="fs-detail-grid">
  <div class="fs-detail-h">Origin</div><div class="fs-detail-h">Destination</div>
  <div class="k" style="grid-column:1">{_airport_line(r.origin_name, r.origin_iata, r.origin_country, r.origin_continent)}</div>
  <div class="k" style="grid-column:2">{_airport_line(r.dest_name, r.dest_iata, r.dest_country, r.dest_continent)}</div>
</div>
<hr style="margin:.6rem 0;border:none;border-top:1px solid #e2e6e8;">
<div class="fs-detail-grid">
  <div class="k">Distance</div><div class="v">{r.distance_km:,.0f} km</div>
  <div class="k">Average price</div><div class="v">&euro;{r.avg_price_eur:,.0f} <span style="color:#8aa;">({r.price_source})</span></div>
  <div class="k">Total demand</div><div class="v">{format_pax(r.demand)} pax/wk</div>
  <div class="k">Total supply</div><div class="v">{format_pax(r.total_supply)} seats/wk</div>
  <div class="k">Supply share (selected airline)</div><div class="v">{share_pct}</div>
  <div class="k">Active airlines on route</div><div class="v">{r.num_airlines}</div>
  <div class="k">Delta (demand &minus; supply)</div><div class="v">{format_pax(r.delta_pax)} pax</div>
  <div class="k">Benefit</div><div class="v">{format_eur(r.benefit_eur)}</div>
</div>
"""


def render_result_card(r: RouteResult, task_value: str) -> None:
    st.markdown(_card_header_html(r, task_value), unsafe_allow_html=True)
    with st.expander("Show Details"):
        st.markdown(_details_html(r), unsafe_allow_html=True)
