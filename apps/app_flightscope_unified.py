"""Unified FlightScope app: collect data and generate route recommendations in one flow."""

from datetime import date, datetime, timezone
import importlib
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

import src.collect_sources as collect_sources
from src.route_database import get_od_by_airline_homebase, get_od_candidate_pool_info
import src.route_database as route_database
import src.recommendation_engine as recommendation_engine


importlib.invalidate_caches()
collect_sources = importlib.reload(collect_sources)
route_database = importlib.reload(route_database)
recommendation_engine = importlib.reload(recommendation_engine)
CollectConfig = collect_sources.CollectConfig
collect_once = collect_sources.collect_once


REGION_BBOX = {
    "Global": {"lamin": -60.0, "lomin": -180.0, "lamax": 85.0, "lomax": 180.0},
    "Europe": {"lamin": 35.0, "lomin": -10.0, "lamax": 71.0, "lomax": 40.0},
    "Asia": {"lamin": -10.0, "lomin": 25.0, "lamax": 80.0, "lomax": 180.0},
    "North America": {"lamin": 7.0, "lomin": -170.0, "lamax": 83.0, "lomax": -50.0},
    "South America": {"lamin": -56.0, "lomin": -82.0, "lamax": 13.0, "lomax": -34.0},
    "Africa": {"lamin": -35.0, "lomin": -20.0, "lamax": 38.0, "lomax": 52.0},
    "Oceania": {"lamin": -50.0, "lomin": 110.0, "lamax": 0.0, "lomax": 180.0},
}

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


st.set_page_config(page_title="FlightScope AI - Unified", layout="wide")
st.title("✈️ FlightScope AI - Unified Planner")
st.caption("Single workflow: Collect market data -> Analyze routes")

available_sources = collect_sources.get_available_sources()
today = date.today()
latest_observed_month = date(today.year, today.month, 1)
year_options = list(range(2024, latest_observed_month.year + 1))

with st.sidebar:
    st.header("Planning Inputs")
    region = st.selectbox("Region", list(REGION_BBOX.keys()), index=0)
    # Filter airlines by selected region (Global shows all)
    if region == "Global":
        region_airlines = list(AIRLINES.keys())
    else:
        region_airlines = [k for k, v in AIRLINES.items() if v.get("region") == region]
    airline_code = st.selectbox(
        "Select Airline",
        region_airlines,
        format_func=lambda x: f"{x} - {AIRLINES[x]['name']}",
    )
    default_analysis_month = latest_observed_month
    _year = st.selectbox(
        "Analysis Year",
        year_options,
        index=year_options.index(default_analysis_month.year),
    )
    month_options = list(range(1, latest_observed_month.month + 1)) if _year == latest_observed_month.year else list(range(1, 13))
    default_month = min(default_analysis_month.month, month_options[-1])
    _month = st.selectbox("Analysis Month", month_options, index=month_options.index(default_month),
                          format_func=lambda m: date(2000, m, 1).strftime("%B"))
    analysis_month = date(_year, _month, 1)
    num_recommendations = st.slider("Number of Recommendations", 1, 10, 3, 1)
    st.caption(f"Observed months only: up to {latest_observed_month.strftime('%B %Y')}")

    with st.expander("Data Source Status", expanded=False):
        st.markdown(f"**Available Data Sources:** {sum(available_sources.values())}/{len(available_sources)}")
        if not available_sources.get("opensky_flights"):
            st.caption("⚠️ OpenSky flights history: OAuth2 not configured (OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET)")
        st.caption("Selected month currently drives model seasonality. OpenSky OD heat uses the latest collected recent-history snapshot, not a month-specific backfill.")
        if not available_sources.get("amadeus"):
            st.caption("⚠️ Amadeus: API key not configured")
        if not available_sources.get("aviationstack"):
            st.caption("⚠️ Aviationstack: API key not configured (AVIATIONSTACK_API_KEY)")
        if not available_sources.get("airlabs"):
            st.caption("⚠️ AirLabs: API key not configured (AIRLABS_API_KEY)")

bbox = REGION_BBOX[region]

if st.button("🔄 Collect Data", type="primary", use_container_width=True):
    cfg = CollectConfig(
        origin="",
        destination="",
        departure_date=analysis_month.isoformat(),
        adults=1,
        dep_iata="",
        arr_iata="",
        eurostat_dataset="",
        geo="DE",
        start_period="2023-01",
        end_period="2026-12",
        lamin=bbox["lamin"],
        lomin=bbox["lomin"],
        lamax=bbox["lamax"],
        lomax=bbox["lomax"],
        use_opensky=available_sources.get("opensky", False),
        use_eurostat=available_sources.get("eurostat", False),
        use_amadeus=available_sources.get("amadeus", False),
        use_aviationstack=available_sources.get("aviationstack", False),
        use_airlabs=available_sources.get("airlabs", False),
    )

    with st.spinner("Collecting data from selected sources..."):
        collect_result = collect_once(cfg)

    # Also collect OpenSky historical departure flights for OD frequency
    import time as _time
    _now = int(_time.time())
    _begin = _now - 7 * 24 * 3600  # last 7 days
    if available_sources.get("opensky_flights"):
        with st.spinner(f"Collecting OpenSky departure history for {region} hubs (last 7 days)..."):
            try:
                flights_result = collect_sources.collect_opensky_flights_region_and_save(region, _begin, _now)
                collect_result["ok"].append({
                    "source": "opensky_flights",
                    "records": flights_result.get("records", 0),
                    "path": flights_result.get("path", ""),
                    "raw_records": flights_result.get("raw_records", 0),
                    "errors": flights_result.get("errors", []),
                })
            except Exception as _exc:
                collect_result["warn"].append({"source": "opensky_flights", "error": str(_exc)})
    else:
        collect_result["warn"].append({
            "source": "opensky_flights",
            "error": "Skipped: missing OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET",
        })

    st.session_state["last_collect_result"] = collect_result

if st.session_state.get("last_collect_result"):
    st.subheader("Collection Summary")
    collect_result = st.session_state["last_collect_result"]
    if collect_result["ok"]:
        st.success(f"Collected from {len(collect_result['ok'])} source(s)")
        rows = []
        for r in collect_result["ok"]:
            row = {"Source": r["source"], "OD pairs / Records": r.get("records", 0)}
            if r.get("raw_records"):
                row["Raw flights"] = r["raw_records"]
            if r.get("errors"):
                row["Errors"] = len(r["errors"])
            rows.append(row)
        st.dataframe(rows, hide_index=True)
    else:
        st.warning("No source collected successfully in this run.")
    if collect_result.get("warn"):
        for w in collect_result["warn"]:
            st.warning(f"{w['source']}: {w['error']}")

month_start = analysis_month.replace(day=1)
if month_start.month == 12:
    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
else:
    month_end = month_start.replace(month=month_start.month + 1, day=1)

collected_data = recommendation_engine.load_latest_collected_data()
collected_data["selected_region"] = region
collected_data["analysis_month"] = analysis_month.month
collected_data.update(
    recommendation_engine.build_route_heat_features(
        hours_back=24,
        period_start=month_start.isoformat(),
        period_end=month_end.isoformat(),
    )
)
recommendations = recommendation_engine.calculate_route_scores(
    collected_data=collected_data,
    airline_code=airline_code,
    num_recommendations=num_recommendations,
)
report = recommendation_engine.generate_recommendation_report(recommendations)

# Check realtime OD availability for display
load_realtime_od = getattr(recommendation_engine, "load_opensky_flights_od_data", None)
flights_meta = load_realtime_od(region) if callable(load_realtime_od) else {}
realtime_od_pairs = flights_meta.get("records", 0)
realtime_age_h = flights_meta.get("data_age_hours", 0.0)
realtime_raw = flights_meta.get("raw_records", 0)
begin_epoch = flights_meta.get("begin_epoch")
end_epoch = flights_meta.get("end_epoch")
if begin_epoch and end_epoch:
    observed_window = (
        f"{datetime.fromtimestamp(begin_epoch, timezone.utc).strftime('%Y-%m-%d')}"
        f" to {datetime.fromtimestamp(end_epoch, timezone.utc).strftime('%Y-%m-%d')} UTC"
    )
else:
    observed_window = "none"
od_label = (
    f"Observed OD heat: {realtime_od_pairs} pairs from {realtime_raw} flights "
    f"| snapshot age {realtime_age_h:.0f}h | window {observed_window}"
    if realtime_od_pairs
    else "Observed OD heat unavailable: using fallback estimates"
)
st.info(
    f"Runtime context -> region={region}, airline={airline_code}, month={analysis_month.month} "
    f"| Live records={collected_data.get('total_live_records', 0)} | {od_label}"
)
st.caption(
    f"Selected month: {analysis_month.strftime('%B %Y')} -> used for model-based seasonality only. "
    f"Current OpenSky OD source window: {observed_window}."
)
candidate_info = get_od_candidate_pool_info(airline_code, region)
candidate_routes = candidate_info["routes"]
candidate_ods = [r["od"] for r in candidate_routes[:8]]
st.caption(
    f"Candidate OD pool: {len(candidate_routes)} routes | sample: "
    + (", ".join(candidate_ods) if candidate_ods else "none")
)
if candidate_info.get("source") == "region-fallback":
    homebase = candidate_info.get("homebase") or "unknown"
    st.caption(
        f"Candidate source: generic {region} fallback. No homebase-matching static routes are configured for airline={airline_code} (homebase={homebase})."
    )

st.subheader("Top Route Recommendations")
st.caption(f"{AIRLINES[airline_code]['name']} | {analysis_month.strftime('%B %Y')} | Region={region}")
st.caption(
    "Score combines [observed] traffic signals, [model-based] seasonality/PAX estimates, and [rule-based] network or distance heuristics."
)

for rec in report["recommendations"]:
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        st.metric("Rank", f"#{rec['rank']}")
    with c2:
        st.markdown(f"### {rec['route']}")
        st.caption(f"OD: {rec['od']}")
    with c3:
        st.metric("Score", f"{rec['score']:.2f}")

    c4, c5, c6, c7 = st.columns([2, 2, 3, 3])
    with c4:
        st.markdown(f"**Est. Passengers**\n{rec['estimated_pax']} pax/month")
    with c5:
        st.markdown(f"**Recommended Aircraft**\n{rec['aircraft']}")
    with c6:
        observed_airlines = ", ".join(rec["observed_airlines"]) if rec["observed_airlines"] else "none"
        market_structure = pd.DataFrame(
            [
                {"Metric": "Observed airlines", "Value": rec["observed_airlines_total"]},
                {"Metric": "Competitors", "Value": rec["competitor_count"]},
                {"Metric": "Target airline seen", "Value": "YES" if rec["target_airline_present"] else "NO"},
                {"Metric": "Target flights seen", "Value": rec["target_airline_observed_flights"]},
                {"Metric": "Opportunity mode", "Value": rec["market_opportunity_label"]},
                {"Metric": "Opportunity score", "Value": rec["market_opportunity_score"]},
                {"Metric": "Airlines observed", "Value": observed_airlines},
            ]
        )
        st.markdown("**Observed Market Structure**")
        st.dataframe(market_structure, hide_index=True, use_container_width=True)
    with c7:
        st.markdown(f"**Rationale**\n{rec['rationale']}")
    st.markdown("---")
