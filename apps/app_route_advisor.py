"""
FlightScope AI - Route Recommendation Engine
Decision support system for airline route planning
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from datetime import datetime
import json
import streamlit as st

import src.recommendation_engine as recommendation_engine


BASE_DIR = Path(__file__).resolve().parent.parent
CONTEXT_PATH = BASE_DIR / "data" / "processed" / "last_collection_context.json"


def load_collection_context() -> dict:
    if not CONTEXT_PATH.exists():
        return {}
    try:
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


st.set_page_config(page_title="FlightScope AI - Route Advisor", layout="wide")

st.title("✈️ FlightScope AI - Route Advisor")
st.caption("Data-Driven Route Recommendation System")

collection_context = load_collection_context()
today = date.today()
latest_observed_month = date(today.year, today.month, 1)
year_options = list(range(2024, latest_observed_month.year + 1))

default_analysis_month = date(2026, 6, 1)
context_departure = str(collection_context.get("departure_date") or "").strip()
if context_departure:
    try:
        dt = datetime.strptime(context_departure, "%Y-%m-%d")
        default_analysis_month = date(dt.year, dt.month, 1)
    except ValueError:
        pass
if default_analysis_month > latest_observed_month:
    default_analysis_month = latest_observed_month

REGION_OPTIONS = ["Global", "Europe", "Asia", "North America", "South America", "Africa", "Oceania"]

# Airline registry
AIRLINES = {
    # Europe
    "LH": {"name": "Lufthansa", "base": "Munich (MUC)", "region": "Europe"},
    "BA": {"name": "British Airways", "base": "London (LHR)", "region": "Europe"},
    "AF": {"name": "Air France", "base": "Paris (CDG)", "region": "Europe"},
    "KL": {"name": "KLM", "base": "Amsterdam (AMS)", "region": "Europe"},
    "IB": {"name": "Iberia", "base": "Madrid (MAD)", "region": "Europe"},
    "VY": {"name": "Vueling", "base": "Barcelona (BCN)", "region": "Europe"},
    "U2": {"name": "easyJet", "base": "London (LGW)", "region": "Europe"},
    "OS": {"name": "Austrian", "base": "Vienna (VIE)", "region": "Europe"},
    "TK": {"name": "Turkish Airlines", "base": "Istanbul (IST)", "region": "Europe"},
    "AZ": {"name": "ITA Airways", "base": "Rome (FCO)", "region": "Europe"},
    # Asia
    "CX": {"name": "Cathay Pacific", "base": "Hong Kong (HKG)", "region": "Asia"},
    "SQ": {"name": "Singapore Airlines", "base": "Singapore (SIN)", "region": "Asia"},
    "NH": {"name": "ANA", "base": "Tokyo (NRT)", "region": "Asia"},
    "JL": {"name": "Japan Airlines", "base": "Tokyo (NRT)", "region": "Asia"},
    "KE": {"name": "Korean Air", "base": "Seoul (ICN)", "region": "Asia"},
    "MH": {"name": "Malaysia Airlines", "base": "Kuala Lumpur (KUL)", "region": "Asia"},
    "TG": {"name": "Thai Airways", "base": "Bangkok (BKK)", "region": "Asia"},
    "CA": {"name": "Air China", "base": "Beijing (PEK)", "region": "Asia"},
    "MU": {"name": "China Eastern", "base": "Shanghai (PVG)", "region": "Asia"},
    "AI": {"name": "Air India", "base": "Delhi (DEL)", "region": "Asia"},
    # North America
    "AA": {"name": "American Airlines", "base": "Dallas (DFW)", "region": "North America"},
    "DL": {"name": "Delta Air Lines", "base": "Atlanta (ATL)", "region": "North America"},
    "UA": {"name": "United Airlines", "base": "Chicago (ORD)", "region": "North America"},
    "WN": {"name": "Southwest Airlines", "base": "Dallas (DAL)", "region": "North America"},
    "AC": {"name": "Air Canada", "base": "Toronto (YYZ)", "region": "North America"},
    "B6": {"name": "JetBlue", "base": "New York (JFK)", "region": "North America"},
    # South America
    "LA": {"name": "LATAM Airlines", "base": "Santiago (SCL)", "region": "South America"},
    "G3": {"name": "Gol Airlines", "base": "São Paulo (GRU)", "region": "South America"},
    "AR": {"name": "Aerolíneas Argentinas", "base": "Buenos Aires (EZE)", "region": "South America"},
    "CM": {"name": "Copa Airlines", "base": "Panama City (PTY)", "region": "South America"},
    # Africa
    "ET": {"name": "Ethiopian Airlines", "base": "Addis Ababa (ADD)", "region": "Africa"},
    "SA": {"name": "South African Airways", "base": "Johannesburg (JNB)", "region": "Africa"},
    "MS": {"name": "EgyptAir", "base": "Cairo (CAI)", "region": "Africa"},
    "AT": {"name": "Royal Air Maroc", "base": "Casablanca (CMN)", "region": "Africa"},
    # Oceania
    "QF": {"name": "Qantas", "base": "Sydney (SYD)", "region": "Oceania"},
    "NZ": {"name": "Air New Zealand", "base": "Auckland (AKL)", "region": "Oceania"},
    "VA": {"name": "Virgin Australia", "base": "Brisbane (BNE)", "region": "Oceania"},
}

with st.sidebar:
    st.header("Analysis Parameters")

    ctx_region = str(collection_context.get("region") or "Europe")
    default_region_idx = REGION_OPTIONS.index(ctx_region) if ctx_region in REGION_OPTIONS else 1
    selected_region = st.selectbox("Region", REGION_OPTIONS, index=default_region_idx)

    if selected_region == "Global":
        region_airlines = list(AIRLINES.keys())
    else:
        region_airlines = [k for k, v in AIRLINES.items() if v.get("region") == selected_region]

    airline_code = st.selectbox(
        "Select Airline",
        region_airlines,
        format_func=lambda x: f"{x} - {AIRLINES[x]['name']}",
    )

    _year = st.selectbox("Analysis Year", year_options, index=year_options.index(default_analysis_month.year))
    month_options = list(range(1, latest_observed_month.month + 1)) if _year == latest_observed_month.year else list(range(1, 13))
    default_month = min(default_analysis_month.month, month_options[-1])
    _month = st.selectbox("Analysis Month", month_options, index=month_options.index(default_month),
                          format_func=lambda m: date(2000, m, 1).strftime("%B"))
    analysis_month = date(_year, _month, 1)
    st.caption(f"Observed months only: up to {latest_observed_month.strftime('%B %Y')}")

    num_recommendations = st.slider(
        "Number of Recommendations",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    st.divider()
    st.markdown(f"**Base:** {AIRLINES[airline_code]['base']}")

# Auto-compute whenever sidebar selection changes (no button needed — no API calls here)
month_start = analysis_month.replace(day=1)
if month_start.month == 12:
    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
else:
    month_end = month_start.replace(month=month_start.month + 1, day=1)

load_data_fn = getattr(recommendation_engine, "load_latest_collected_data", lambda: {})
collected_data = load_data_fn()
collected_data["selected_region"] = selected_region
collected_data["analysis_month"] = analysis_month.month
heat_fn = getattr(recommendation_engine, "build_route_heat_features", lambda: {})
try:
    collected_data.update(
        heat_fn(
            hours_back=24,
            period_start=month_start.isoformat(),
            period_end=month_end.isoformat(),
        )
    )
except TypeError:
    collected_data.update(heat_fn())
recommendations = recommendation_engine.calculate_route_scores(
    collected_data=collected_data,
    airline_code=airline_code,
    num_recommendations=num_recommendations,
)
report = recommendation_engine.generate_recommendation_report(recommendations)

if collected_data.get("has_live_data"):
    st.info(
        "Using cached live data from: "
        + ", ".join(collected_data.get("sources_used", []))
        + f" | Total records: {collected_data.get('total_live_records', 0)}"
    )
else:
    st.warning("No cached live data found under data/raw. Scoring is based on route priors only.")

st.subheader("✅ Top Route Recommendations")
st.caption(f"Analysis for {AIRLINES[airline_code]['name']} | {analysis_month.strftime('%B %Y')} | Region: {selected_region}")
st.caption(f"Runtime context -> region={selected_region}, airline={airline_code}, month={analysis_month.month}")

for i, rec in enumerate(report["recommendations"], 1):
    with st.container():
        col_rank, col_route, col_score = st.columns([1, 3, 1])
        with col_rank:
            st.metric("Rank", f"#{rec['rank']}")
        with col_route:
            st.markdown(f"### {rec['route']}")
            st.caption(f"OD: {rec['od']}")
        with col_score:
            st.metric("Score", f"{rec['score']:.2f}")

        st.markdown("---")

        col_pax, col_ac, col_reason = st.columns([2, 2, 3])
        with col_pax:
            st.markdown(f"**Est. Passengers**\n{rec['estimated_pax']} pax/month")
        with col_ac:
            st.markdown(f"**Recommended Aircraft**\n{rec['aircraft']}")
        with col_reason:
            st.markdown(f"**Rationale**\n{rec['rationale']}")

        st.write("")

st.divider()
st.markdown("### How It Works")
st.markdown("""
1. **Data Collection**: System aggregates real-time market data (prices, demand signals, competitive intensity)
2. **Scoring**: Each European route is evaluated on:
   - Demand indicators (search volume, frequency potential)
   - Price attractiveness (revenue opportunity)
   - Competitive landscape (market gaps)
   - Operational efficiency (distance, turnaround)
3. **Recommendation**: Top-ranked routes with aircraft sizing based on forecasted passenger volume
4. **Decision Support**: Airline can approve/reject with full transparency on scoring rationale
""")
