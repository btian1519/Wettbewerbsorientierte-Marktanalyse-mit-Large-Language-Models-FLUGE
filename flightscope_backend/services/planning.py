"""Backend orchestration services.

These two functions are the server-side flows that were previously inlined at
module top level in apps/app_flightscope_unified.py, interleaved with Streamlit
calls:

* ``run_collection``  -> the "Collect Data" button handler (lines that built
  CollectConfig, ran collect_once and appended OpenSky flight history).
* ``build_analysis``  -> the analysis pipeline (load collected data, score
  routes, build the report, filter decision-policy rows, compute coverage and
  planning summaries).

The isolation is purely structural: the Streamlit display / input calls
(``st.spinner``, ``st.session_state``, ``st.info``, widgets, ...) were removed,
and the values that used to come from sidebar widgets are now function
parameters. Every computation is preserved unchanged. ``run_collection`` returns
the collect_result dict (previously stored in ``st.session_state``);
``build_analysis`` returns every computed value in a dict for a future UI to
render.
"""

from datetime import datetime, timezone

import pandas as pd

from ..engine import (
    CollectConfig,
    PROCESSED_DIR,
    collect_once,
    collect_sources,
    get_od_candidate_pool_info,
    recommendation_engine,
)
from ..core.analysis import (
    build_planning_summary_lines,
    summarize_action_coverage,
    summarize_route_coverage,
)
from ..core.reports import (
    load_check24_snapshot_df,
    load_check24_snapshot_summary,
    load_decision_recommendations,
    load_json_report,
)


def run_collection(bbox: dict, effective_month, region: str, available_sources: dict) -> dict:
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

    collect_result = collect_once(cfg)

    # Also collect OpenSky historical departure flights for OD frequency
    import time as _time
    _now = int(_time.time())
    _begin = _now - 7 * 24 * 3600  # last 7 days
    if available_sources.get("opensky_flights"):
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

    return collect_result


def build_analysis(region: str, airline_code: str, effective_month, planning_horizon_months: int, num_recommendations: int) -> dict:
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
    runtime_context = (
        f"Runtime context -> region={region}, airline={airline_code}, effective_month={effective_month.month}, horizon={planning_horizon_months}m "
        f"| Live records={collected_data.get('total_live_records', 0)} | {od_label}"
    )
    planning_context_caption = (
        f"Planning horizon: next {planning_horizon_months} month(s) | Effective month: {effective_month.strftime('%B %Y')} -> used for seasonality scenario only. "
        f"Current OpenSky OD source window remains {observed_window}."
    )
    candidate_info = get_od_candidate_pool_info(airline_code, region)
    candidate_routes = candidate_info["routes"]
    candidate_ods = [r["od"] for r in candidate_routes[:8]]

    source_overlap_report = load_json_report(PROCESSED_DIR / "source_overlap_report.json")
    baseline_report = load_json_report(PROCESSED_DIR / "baseline_model_report.json")
    check24_snapshot_summary = load_check24_snapshot_summary(PROCESSED_DIR / "check24_offer_snapshot.csv")
    check24_snapshot_df = load_check24_snapshot_df(PROCESSED_DIR / "check24_offer_snapshot.csv")
    decision_recommendations_df = load_decision_recommendations(PROCESSED_DIR / "decision_policy_recommendations.json")

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

    return {
        "collected_data": collected_data,
        "recommendations": recommendations,
        "report": report,
        "flights_meta": flights_meta,
        "realtime_od_pairs": realtime_od_pairs,
        "realtime_age_h": realtime_age_h,
        "realtime_raw": realtime_raw,
        "begin_epoch": begin_epoch,
        "end_epoch": end_epoch,
        "observed_window": observed_window,
        "od_label": od_label,
        "runtime_context": runtime_context,
        "planning_context_caption": planning_context_caption,
        "candidate_info": candidate_info,
        "candidate_routes": candidate_routes,
        "candidate_ods": candidate_ods,
        "source_overlap_report": source_overlap_report,
        "baseline_report": baseline_report,
        "check24_snapshot_summary": check24_snapshot_summary,
        "check24_snapshot_df": check24_snapshot_df,
        "decision_recommendations_df": decision_recommendations_df,
        "filtered_decisions": filtered_decisions,
        "decision_lookup": decision_lookup,
        "action_coverage_title": action_coverage_title,
        "action_coverage_caption": action_coverage_caption,
        "route_coverage_title": route_coverage_title,
        "route_coverage_caption": route_coverage_caption,
        "growth_summary_lines": growth_summary_lines,
        "defend_summary_lines": defend_summary_lines,
    }
