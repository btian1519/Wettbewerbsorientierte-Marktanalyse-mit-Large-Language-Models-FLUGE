"""Unified FlightScope app: collect data and generate route recommendations in one flow."""

from datetime import date, datetime, timezone
import importlib
import json
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
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"


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


def load_json_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_check24_snapshot_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        snapshot_df = pd.read_csv(path)
    except Exception:
        return {}
    if snapshot_df.empty:
        return {"rows": 0}

    lead_time_series = pd.to_numeric(snapshot_df.get("lead_time_days"), errors="coerce").dropna()
    return {
        "rows": int(len(snapshot_df)),
        "od_count": int(snapshot_df["od"].nunique()) if "od" in snapshot_df else 0,
        "carrier_count": int(snapshot_df["outbound_carrier"].nunique()) if "outbound_carrier" in snapshot_df else 0,
        "lead_time_min": int(lead_time_series.min()) if not lead_time_series.empty else 0,
        "lead_time_max": int(lead_time_series.max()) if not lead_time_series.empty else 0,
    }


def load_check24_snapshot_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        snapshot_df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    if snapshot_df.empty:
        return snapshot_df

    for column in ["lead_time_days", "price_eur", "summary_direct_min_price_eur"]:
        if column in snapshot_df.columns:
            snapshot_df[column] = pd.to_numeric(snapshot_df[column], errors="coerce")
    return snapshot_df


def load_decision_recommendations(path: Path) -> pd.DataFrame:
    payload = load_json_report(path)
    if not isinstance(payload, list) or not payload:
        return pd.DataFrame()
    try:
        decision_df = pd.DataFrame(payload)
    except Exception:
        return pd.DataFrame()
    if decision_df.empty:
        return decision_df

    for column in [
        "current_airline_od_flights",
        "current_airline_od_share",
        "predicted_future_airline_od_flights",
        "predicted_future_airline_od_share",
        "predicted_share_delta",
        "current_route_avg_seats",
        "current_target_airline_avg_seats",
        "current_yield_proxy_eur_per_1000km",
        "confidence",
    ]:
        if column in decision_df.columns:
            decision_df[column] = pd.to_numeric(decision_df[column], errors="coerce")
    return decision_df


def format_support_badge(level: str) -> str:
    level_text = str(level or "unknown").strip().lower()
    if level_text == "high":
        return "HIGH"
    if level_text == "medium":
        return "MEDIUM"
    if level_text == "baseline":
        return "BASELINE"
    if level_text == "sparse":
        return "SPARSE"
    return level_text.upper() or "UNKNOWN"


def format_proxy_value(value: float | int | None, suffix: str = "") -> str:
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value) or float(numeric_value) <= 0:
        return "n/a"
    return f"{float(numeric_value):.1f}{suffix}"


def has_auxiliary_capacity_or_yield_support(decision: pd.Series | dict) -> bool:
    route_seats = pd.to_numeric((decision.get("current_route_avg_seats") if isinstance(decision, dict) else decision.get("current_route_avg_seats")), errors="coerce")
    airline_seats = pd.to_numeric((decision.get("current_target_airline_avg_seats") if isinstance(decision, dict) else decision.get("current_target_airline_avg_seats")), errors="coerce")
    yield_proxy = pd.to_numeric((decision.get("current_yield_proxy_eur_per_1000km") if isinstance(decision, dict) else decision.get("current_yield_proxy_eur_per_1000km")), errors="coerce")
    return any(not pd.isna(value) and float(value) > 0 for value in [route_seats, airline_seats, yield_proxy])


def has_positive_yield_proxy(decision: pd.Series | dict) -> bool:
    yield_proxy = pd.to_numeric((decision.get("current_yield_proxy_eur_per_1000km") if isinstance(decision, dict) else decision.get("current_yield_proxy_eur_per_1000km")), errors="coerce")
    return not pd.isna(yield_proxy) and float(yield_proxy) > 0


def add_months(month_start: date, months_to_add: int) -> date:
    ts = pd.Timestamp(month_start) + pd.DateOffset(months=months_to_add)
    return date(int(ts.year), int(ts.month), 1)


def format_month_window(start_month: date, end_month: date) -> str:
    if start_month.year == end_month.year and start_month.month == end_month.month:
        return start_month.strftime("%B %Y")
    if start_month.year == end_month.year:
        return f"{start_month.strftime('%B')}-{end_month.strftime('%B %Y')}"
    return f"{start_month.strftime('%B %Y')}-{end_month.strftime('%B %Y')}"


def build_planning_recommendation(action: str, od: str, effective_month: date, planning_horizon_months: int) -> str:
    full_end = add_months(effective_month, max(planning_horizon_months - 1, 0))
    near_end = add_months(effective_month, max(min(planning_horizon_months, 3) - 1, 0))
    near_window = format_month_window(effective_month, near_end)
    full_window = format_month_window(effective_month, full_end)
    late_start = add_months(effective_month, 3) if planning_horizon_months > 3 else effective_month
    late_window = format_month_window(late_start, full_end)

    action_text = str(action or "").strip().lower()
    if action_text == "launch route":
        if planning_horizon_months > 3:
            return f"Planning recommendation: validate demand and slots in {near_window}, then target a route launch on {od} in {late_window}."
        return f"Planning recommendation: use {full_window} to validate demand and prepare a potential launch on {od}."
    if action_text == "upgauge":
        return f"Planning recommendation: plan an aircraft upgauge on {od} in {near_window} if operational constraints allow."
    if action_text == "add frequency":
        return f"Planning recommendation: add frequency on {od} in {near_window} rather than committing to larger gauge first."
    if action_text == "reduce / defend selectively":
        if planning_horizon_months > 3:
            return f"Planning recommendation: in {near_window}, defend {od} selectively and avoid adding capacity; reassess again in {late_window}."
        return f"Planning recommendation: in {full_window}, defend {od} selectively and avoid adding capacity."
    return f"Planning recommendation: keep the current plan on {od} through {full_window}; no capacity change is recommended yet."


def build_planning_summary_lines(filtered_decisions: pd.DataFrame, effective_month: date, planning_horizon_months: int, per_bucket_limit: int = 3) -> tuple[list[str], list[str]]:
    if filtered_decisions.empty:
        return [], []

    growth_actions = {"launch route", "upgauge", "add frequency"}
    defend_actions = {"reduce / defend selectively"}
    growth_candidates = filtered_decisions[
        filtered_decisions["action"].astype(str).str.lower().isin(growth_actions)
    ].head(per_bucket_limit)
    defend_candidates = filtered_decisions[
        filtered_decisions["action"].astype(str).str.lower().isin(defend_actions)
    ].head(per_bucket_limit)

    growth_lines: list[str] = []
    defend_lines: list[str] = []

    for _, decision in growth_candidates.iterrows():
        action_text = str(decision.get("action") or "").strip().lower()
        od = str(decision.get("od") or "")
        planning_text = build_planning_recommendation(action_text, od, effective_month, planning_horizon_months)
        compact_text = planning_text.replace("Planning recommendation: ", "")
        growth_lines.append(f"{od}: {compact_text}")

    for _, decision in defend_candidates.iterrows():
        action_text = str(decision.get("action") or "").strip().lower()
        od = str(decision.get("od") or "")
        planning_text = build_planning_recommendation(action_text, od, effective_month, planning_horizon_months)
        compact_text = planning_text.replace("Planning recommendation: ", "")
        defend_lines.append(f"{od}: {compact_text}")

    return growth_lines, defend_lines


def summarize_action_coverage(filtered_decisions: pd.DataFrame) -> tuple[str, str]:
    if filtered_decisions.empty:
        return (
            "Action coverage: NONE",
            "No model-action rows are available for this airline in the latest decision batch.",
        )

    support_series = (
        filtered_decisions.get("support_level", pd.Series(dtype="object"))
        .fillna("unknown")
        .astype(str)
        .str.lower()
    )
    positive_yield_count = int(
        sum(has_positive_yield_proxy(row) for _, row in filtered_decisions.iterrows())
    )
    aux_support_count = int(
        sum(has_auxiliary_capacity_or_yield_support(row) for _, row in filtered_decisions.iterrows())
    )
    total_rows = int(len(filtered_decisions))

    if any(level in {"high", "medium", "sparse"} for level in support_series):
        return (
            "Action coverage: OBSERVED + AUXILIARY",
            f"{total_rows} OD action rows are available; {positive_yield_count} currently have positive web-yield support and {aux_support_count} have matched AirLabs or Check24 evidence.",
        )
    if aux_support_count > 0:
        return (
            "Action coverage: MIXED",
            f"{total_rows} OD action rows are available; {positive_yield_count} currently have positive web-yield support and {aux_support_count} include matched capacity or web-yield evidence.",
        )
    return (
        "Action coverage: BASELINE ONLY",
        f"{total_rows} OD action rows are available, but the current display still relies on baseline OpenSky history without matched AirLabs or Check24 support.",
    )


def summarize_route_coverage(report: dict) -> tuple[str, str]:
    recommendations = report.get("recommendations") or []
    if not recommendations:
        return (
            "Route coverage: NONE",
            "No observed-supported route cards are available in the current market-data window.",
        )

    supported_routes = len(recommendations)
    observed_target_routes = sum(1 for rec in recommendations if rec.get("target_airline_observed_flights", 0) > 0)
    return (
        "Route coverage: OBSERVED-SUPPORTED",
        f"{supported_routes} route cards are shown and {observed_target_routes} include directly observed flights from the selected airline in the current window.",
    )


st.set_page_config(page_title="FlightScope AI - Unified", layout="wide")
st.title("✈️ FlightScope AI - Unified Planner")
st.caption("Single workflow: Collect market data -> Analyze routes")

available_sources = collect_sources.get_available_sources()
today = date.today()
latest_observed_month = date(today.year, today.month, 1)
year_options = list(range(2024, latest_observed_month.year + 1))
PLANNING_HORIZON_OPTIONS = {
    "Next 1 month": 1,
    "Next 3 months": 3,
    "Next 6 months": 6,
}

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
    planning_horizon_label = st.selectbox("Planning Horizon", list(PLANNING_HORIZON_OPTIONS.keys()), index=1)
    planning_horizon_months = PLANNING_HORIZON_OPTIONS[planning_horizon_label]
    default_effective_month = latest_observed_month
    _year = st.selectbox(
        "Effective Year",
        year_options,
        index=year_options.index(default_effective_month.year),
    )
    month_options = list(range(1, latest_observed_month.month + 1)) if _year == latest_observed_month.year else list(range(1, 13))
    default_month = min(default_effective_month.month, month_options[-1])
    _month = st.selectbox("Effective Month", month_options, index=month_options.index(default_month),
                          format_func=lambda m: date(2000, m, 1).strftime("%B"))
    effective_month = date(_year, _month, 1)
    num_recommendations = st.slider("Number of Recommendations", 1, 10, 3, 1)
    st.caption(f"Observed months only: up to {latest_observed_month.strftime('%B %Y')}")

    with st.expander("Data Source Status", expanded=False):
        st.markdown(f"**Available Data Sources:** {sum(available_sources.values())}/{len(available_sources)}")
        if not available_sources.get("opensky_flights"):
            st.caption("⚠️ OpenSky flights history: OAuth2 not configured (OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET)")
        st.caption("Effective Month currently drives the seasonality scenario. Observed OD heat still uses the latest collected recent-history snapshot, not a month-specific backfill.")
        if not available_sources.get("amadeus"):
            st.caption("⚠️ Amadeus: API key not configured")
        if not available_sources.get("aviationstack"):
            st.caption("⚠️ Aviationstack: API key not configured (AVIATIONSTACK_API_KEY)")
        if not available_sources.get("airlabs"):
            st.caption("⚠️ AirLabs: API key not configured (AIRLABS_API_KEY)")
        if available_sources.get("check24"):
            st.caption("ℹ️ Check24 scraping is available in the OD collector app. It is not used in this region-wide planner because Check24 requires a concrete OD/date query.")

bbox = REGION_BBOX[region]

if st.button("🔄 Collect Data", type="primary", use_container_width=True):
    cfg = CollectConfig(
        origin="",
        destination="",
        departure_date=effective_month.isoformat(),
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
        use_check24=False,
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

collected_data = recommendation_engine.load_latest_collected_data()
collected_data["selected_region"] = region
collected_data["analysis_month"] = effective_month.month
collected_data["planning_horizon_months"] = planning_horizon_months
collected_data.update(
    recommendation_engine.build_route_heat_features(
        hours_back=24,
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
    f"Runtime context -> region={region}, airline={airline_code}, effective_month={effective_month.month}, horizon={planning_horizon_months}m "
    f"| Live records={collected_data.get('total_live_records', 0)} | {od_label}"
)
st.caption(
    f"Planning horizon: next {planning_horizon_months} month(s) | Effective month: {effective_month.strftime('%B %Y')} -> used for seasonality scenario only. "
    f"Current OpenSky OD source window remains {observed_window}."
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

source_overlap_report = load_json_report(PROCESSED_DIR / "source_overlap_report.json")
baseline_report = load_json_report(PROCESSED_DIR / "baseline_model_report.json")
check24_snapshot_summary = load_check24_snapshot_summary(PROCESSED_DIR / "check24_offer_snapshot.csv")
check24_snapshot_df = load_check24_snapshot_df(PROCESSED_DIR / "check24_offer_snapshot.csv")
decision_recommendations_df = load_decision_recommendations(PROCESSED_DIR / "decision_policy_recommendations.json")

with st.expander("Training Diagnostics", expanded=False):
    overlap_cols = st.columns(3)
    aviationstack_overlap = (source_overlap_report.get("aviationstack_vs_opensky") or {})
    airlabs_overlap = (source_overlap_report.get("airlabs_vs_opensky") or {})
    regression = (baseline_report.get("regression") or {})
    with overlap_cols[0]:
        st.metric(
            "AirLabs OD overlap",
            f"{airlabs_overlap.get('od_overlap_count', 0)}",
            delta=f"{100 * airlabs_overlap.get('od_overlap_ratio_vs_base', 0.0):.1f}% of OpenSky ODs",
        )
    with overlap_cols[1]:
        st.metric(
            "Aviationstack OD overlap",
            f"{aviationstack_overlap.get('od_overlap_count', 0)}",
            delta=f"{100 * aviationstack_overlap.get('od_overlap_ratio_vs_base', 0.0):.1f}% of OpenSky ODs",
        )
    with overlap_cols[2]:
        mae_value = regression.get("mae")
        naive_mae_value = regression.get("naive_mae")
        if mae_value is not None and naive_mae_value is not None:
            st.metric("Baseline MAE", f"{mae_value:.3f}", delta=f"vs naive {naive_mae_value:.3f}")
        else:
            st.metric("Baseline MAE", "n/a")

    aviationstack_overlap_ratio = float(aviationstack_overlap.get("od_overlap_ratio_vs_base", 0.0) or 0.0)
    airlabs_overlap_ratio = float(airlabs_overlap.get("od_overlap_ratio_vs_base", 0.0) or 0.0)
    if aviationstack_overlap_ratio < 0.05:
        st.warning(
            "Aviationstack currently overlaps with less than 5% of the OpenSky OD training slice. "
            "Treat Aviationstack features as sparse auxiliary evidence, not as a primary explanation source."
        )
    if airlabs_overlap_ratio >= 0.2:
        st.success(
            "AirLabs currently has materially better overlap with the OpenSky training slice, so its route-level features are more defensible in the current baseline."
        )

    check24_cols = st.columns(3)
    with check24_cols[0]:
        st.metric("Check24 snapshots", f"{check24_snapshot_summary.get('rows', 0)} offers")
    with check24_cols[1]:
        st.metric("Check24 OD coverage", f"{check24_snapshot_summary.get('od_count', 0)} ODs")
    with check24_cols[2]:
        lead_min = check24_snapshot_summary.get("lead_time_min", 0)
        lead_max = check24_snapshot_summary.get("lead_time_max", 0)
        st.metric("Check24 lead time", f"{lead_min}-{lead_max} days")

    st.caption(
        "Auxiliary-source coverage matters: AirLabs currently overlaps much more with the OpenSky training slice than Aviationstack. "
        "Check24 web snapshots already carry explicit crawl time and travel-date semantics, but current historical OD overlap is still sparse."
    )
    sample_pairs = airlabs_overlap.get("sample_overlap_pairs") or []
    if sample_pairs:
        st.caption("Sample AirLabs airline-OD overlap: " + ", ".join(sample_pairs[:6]))
    if not check24_snapshot_df.empty and {"lead_time_days", "price_eur"}.issubset(check24_snapshot_df.columns):
        chart_df = (
            check24_snapshot_df.dropna(subset=["lead_time_days", "price_eur"])
            .sort_values(["od", "lead_time_days", "price_eur"])
            [["od", "lead_time_days", "price_eur"]]
        )
        if not chart_df.empty:
            st.markdown("**Check24 Lead-Time Snapshot**")
            st.caption("Observed web offers by lead time. This is a pricing/availability signal, not a flown-history signal.")
            st.line_chart(chart_df, x="lead_time_days", y="price_eur", color="od")

filtered_decisions = pd.DataFrame()
if not decision_recommendations_df.empty and "airline" in decision_recommendations_df.columns:
    filtered_decisions = decision_recommendations_df[decision_recommendations_df["airline"] == airline_code].copy()
    if not filtered_decisions.empty:
        filtered_decisions["has_positive_yield_proxy"] = (
            pd.to_numeric(filtered_decisions.get("current_yield_proxy_eur_per_1000km"), errors="coerce").fillna(0) > 0
        ).astype(int)
        filtered_decisions["has_positive_aux_support"] = (
            (
                pd.to_numeric(filtered_decisions.get("current_route_avg_seats"), errors="coerce").fillna(0) > 0
            )
            | (
                pd.to_numeric(filtered_decisions.get("current_target_airline_avg_seats"), errors="coerce").fillna(0) > 0
            )
            | (
                pd.to_numeric(filtered_decisions.get("current_yield_proxy_eur_per_1000km"), errors="coerce").fillna(0) > 0
            )
        ).astype(int)
        filtered_decisions = filtered_decisions.sort_values(
            ["od", "has_positive_yield_proxy", "has_positive_aux_support", "confidence", "predicted_share_delta", "predicted_future_airline_od_flights"],
            ascending=[True, False, False, False, False, False],
        )
        filtered_decisions = filtered_decisions.drop_duplicates(subset=["od"], keep="first")
        filtered_decisions = filtered_decisions.sort_values(
            ["has_positive_yield_proxy", "has_positive_aux_support", "confidence", "predicted_share_delta", "predicted_future_airline_od_flights"],
            ascending=[False, False, False, False, False],
        )

decision_lookup = {}
if not filtered_decisions.empty and "od" in filtered_decisions.columns:
    decision_lookup = {
        str(row["od"]): row.to_dict()
        for _, row in filtered_decisions.drop_duplicates(subset=["od"]).iterrows()
    }

action_coverage_title, action_coverage_caption = summarize_action_coverage(filtered_decisions)
route_coverage_title, route_coverage_caption = summarize_route_coverage(report)
growth_summary_lines, defend_summary_lines = build_planning_summary_lines(
    filtered_decisions,
    effective_month,
    planning_horizon_months,
    per_bucket_limit=min(num_recommendations, 3),
)

st.subheader("Coverage Status")
coverage_col_1, coverage_col_2 = st.columns(2)
with coverage_col_1:
    st.info(action_coverage_title)
    st.caption(action_coverage_caption)
with coverage_col_2:
    st.info(route_coverage_title)
    st.caption(route_coverage_caption)

st.subheader("Planning Summary")
summary_col_1, summary_col_2 = st.columns(2)
with summary_col_1:
    st.markdown("**Growth / Launch Moves**")
    if growth_summary_lines:
        for line in growth_summary_lines:
            st.caption(line)
    else:
        st.caption(
            f"No supported growth or launch move is currently recommended for {AIRLINES[airline_code]['name']} in this {planning_horizon_months}-month planning window."
        )
with summary_col_2:
    st.markdown("**Defend / Reduce Moves**")
    if defend_summary_lines:
        for line in defend_summary_lines:
            st.caption(line)
    else:
        st.caption("No defend or selective-reduction move is currently prioritized in the displayed recommendation set.")

st.subheader("Model-Based Action Suggestions")
if filtered_decisions.empty:
    st.caption(
        "No model-based action suggestions are currently available for this airline in the latest decision-policy batch. "
        "Run scripts/generate_decision_recommendations.py after refreshing the training dataset if needed."
    )
else:
    st.caption(
        "These actions come from the baseline future-flights and future-share models plus a transparent decision policy. "
        "They are shown separately from the heuristic route-ranking block below."
    )
    st.caption(
        "Rows with positive web-yield evidence are shown first when available; after that, rows with any matched AirLabs or Check24 auxiliary support are prioritized ahead of baseline-only rows."
    )
    st.caption(
        "If capacity or yield evidence shows as n/a, that means the current row has no matched AirLabs or Check24 auxiliary support yet. "
        "It does not mean true aircraft size or route yield is zero."
    )
    for _, decision in filtered_decisions.head(num_recommendations).iterrows():
        d1, d2, d3 = st.columns([2, 2, 3])
        planning_text = build_planning_recommendation(
            str(decision.get("action") or ""),
            str(decision.get("od") or ""),
            effective_month,
            planning_horizon_months,
        )
        with d1:
            st.markdown(f"### {decision['od']}")
            st.caption(f"Action: {decision['action']}")
            evidence_tags = []
            if has_positive_yield_proxy(decision):
                evidence_tags.append("PRICE-BACKED")
            elif has_auxiliary_capacity_or_yield_support(decision):
                evidence_tags.append("AUX-SUPPORTED")
            else:
                evidence_tags.append("BASELINE-ONLY")
            st.caption("Evidence status: " + " | ".join(evidence_tags))
        with d2:
            st.metric("Confidence", f"{float(decision['confidence']):.2f}")
        with d3:
            delta_share = float(decision.get("predicted_share_delta") or 0.0)
            predicted_flights = float(decision.get("predicted_future_airline_od_flights") or 0.0)
            st.markdown(
                "**Predicted state**\n"
                f"Flights: {predicted_flights:.1f} | "
                f"Share: {float(decision.get('predicted_future_airline_od_share') or 0.0):.3f} | "
                f"ΔShare: {delta_share:+.3f}"
            )
        st.caption(planning_text)
        seat_route = format_proxy_value(decision.get("current_route_avg_seats"), " seats")
        seat_airline = format_proxy_value(decision.get("current_target_airline_avg_seats"), " seats")
        yield_proxy = format_proxy_value(decision.get("current_yield_proxy_eur_per_1000km"), " EUR/1000km")
        st.caption(
            "Capacity / yield evidence: "
            f"Route avg seats {seat_route} | "
            f"Target-airline avg seats {seat_airline} | "
            f"Web yield proxy {yield_proxy}"
        )
        if not has_auxiliary_capacity_or_yield_support(decision):
            st.caption("Interpretation note: this row currently relies on baseline OpenSky history only; auxiliary capacity or web-price support has not matched this OD yet.")
        support_level = str(decision.get("support_level") or "unknown")
        scoring_split = str(decision.get("scoring_split") or "unknown").upper()
        support_sources = decision.get("support_sources") or []
        badge = format_support_badge(support_level)
        if isinstance(support_sources, list) and support_sources:
            st.caption(
                f"Support level: {badge} | Scoring split: {scoring_split} | Sources: " + ", ".join(str(item) for item in support_sources)
            )
        else:
            st.caption(f"Support level: {badge} | Scoring split: {scoring_split}")
        rationale_lines = decision.get("rationale") or []
        if isinstance(rationale_lines, list) and rationale_lines:
            st.caption(" | ".join(str(item) for item in rationale_lines))
        else:
            st.caption("No rationale available.")
        st.markdown("---")

st.subheader("Top Route Recommendations")
st.caption(f"{AIRLINES[airline_code]['name']} | Effective {effective_month.strftime('%B %Y')} | Horizon next {planning_horizon_months} month(s) | Region={region}")
st.caption(
    "Score combines [observed] traffic signals, [model-based] seasonality/PAX estimates, and [rule-based] network or distance heuristics."
)
st.caption("Observed-supported only: routes without current OD support are intentionally suppressed instead of being inferred from static priors.")

if not report["recommendations"]:
    st.caption(
        "No route recommendations are shown because the current candidate pool has no observed OD support in the latest collected market data. "
        "This app now suppresses unsupported routes instead of inferring them from static priors alone."
    )
else:
    for rec in report["recommendations"]:
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            st.metric("Rank", f"#{rec['rank']}")
        with c2:
            st.markdown(f"### {rec['route']}")
            st.caption(f"OD: {rec['od']}")
        with c3:
            st.metric("Score", f"{rec['score']:.2f}")

        linked_decision = decision_lookup.get(str(rec.get("od") or ""))
        if linked_decision:
            support_badge = format_support_badge(str(linked_decision.get("support_level") or "unknown"))
            scoring_split = str(linked_decision.get("scoring_split") or "unknown").upper()
            support_sources = linked_decision.get("support_sources") or []
            route_planning_text = build_planning_recommendation(
                str(linked_decision.get("action") or ""),
                str(linked_decision.get("od") or rec.get("od") or ""),
                effective_month,
                planning_horizon_months,
            )
            decision_caption = (
                f"Model action: {linked_decision.get('action', 'n/a')} | "
                f"Confidence {float(linked_decision.get('confidence') or 0.0):.2f} | "
                f"Support {support_badge} | Split {scoring_split}"
            )
            st.caption(decision_caption)
            st.caption(route_planning_text)
            st.caption(
                "Model capacity/yield evidence: "
                f"Route seats {format_proxy_value(linked_decision.get('current_route_avg_seats'), ' seats')} | "
                f"Airline seats {format_proxy_value(linked_decision.get('current_target_airline_avg_seats'), ' seats')} | "
                f"Yield {format_proxy_value(linked_decision.get('current_yield_proxy_eur_per_1000km'), ' EUR/1000km')}"
            )
            if not has_auxiliary_capacity_or_yield_support(linked_decision):
                st.caption("Interpretation note: no matched AirLabs or Check24 auxiliary evidence for this route card yet; the action is currently driven by baseline OpenSky history and modeled demand/share movement.")
            if isinstance(support_sources, list) and support_sources:
                st.caption("Action support sources: " + ", ".join(str(item) for item in support_sources))

        c4, c5, c6, c7 = st.columns([2, 2, 3, 3])
        with c4:
            st.markdown(f"**Est. Passengers**\n{rec['estimated_pax']} pax/month")
        with c5:
            st.markdown(f"**Recommended Aircraft**\n{rec['aircraft']}")
        with c6:
            observed_airlines = ", ".join(rec["observed_airlines"]) if rec["observed_airlines"] else "none"
            market_structure = pd.DataFrame(
                [
                    {"Metric": "Observed airlines", "Value": str(rec["observed_airlines_total"])},
                    {"Metric": "Competitors", "Value": str(rec["competitor_count"])},
                    {"Metric": "Target airline seen", "Value": "YES" if rec["target_airline_present"] else "NO"},
                    {"Metric": "Target flights seen", "Value": str(rec["target_airline_observed_flights"])},
                    {"Metric": "Opportunity mode", "Value": str(rec["market_opportunity_label"])},
                    {"Metric": "Opportunity score", "Value": str(rec["market_opportunity_score"])},
                    {"Metric": "Airlines observed", "Value": str(observed_airlines)},
                ]
            )
            st.markdown("**Observed Market Structure**")
            st.dataframe(market_structure, hide_index=True, use_container_width=True)
        with c7:
            st.markdown(f"**Rationale**\n{rec['rationale']}")
        st.markdown("---")
