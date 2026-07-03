"""Report / snapshot loaders.

Data-access functions extracted verbatim from apps/app_flightscope_unified.py.
They read processed reports and snapshots from disk and normalize them into
plain dicts / pandas DataFrames. No UI, no behavior change.
"""

import json
from pathlib import Path

import pandas as pd


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
