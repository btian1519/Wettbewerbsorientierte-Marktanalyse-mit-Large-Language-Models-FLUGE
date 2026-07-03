"""Analysis / formatting / planning-text logic.

Pure functions extracted verbatim from apps/app_flightscope_unified.py. These
compute badges, proxy formatting, evidence predicates, planning recommendation
text and coverage summaries. No UI, no behavior change.
"""

from datetime import date

import pandas as pd


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


def has_support_source(decision: pd.Series | dict, source_name: str) -> bool:
    sources = decision.get("support_sources") if isinstance(decision, dict) else decision.get("support_sources")
    if not isinstance(sources, list):
        return False
    return any(str(item).strip().lower() == source_name.strip().lower() for item in sources)


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
