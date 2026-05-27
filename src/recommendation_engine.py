"""
Route recommendation engine using collected market data.
Combines price signals, demand proxies, and competitive intensity.
"""

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
from .route_database import get_homebase_for_airline, get_od_by_airline_homebase, get_routes_by_region, recommend_aircraft


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


@dataclass
class RouteScore:
    od: str
    origin: str
    destination: str
    score: float
    estimated_pax: int
    recommended_aircraft: str
    observed_airlines_total: int
    observed_airlines: List[str]
    competitor_count: int
    target_airline_present: bool
    target_airline_observed_flights: int
    market_opportunity_score: float
    market_opportunity_label: str
    reasoning: List[str]


def _read_latest_payload(source: str) -> Dict[str, Any]:
    source_dir = RAW_DIR / source
    if not source_dir.exists():
        return {}

    candidates = sorted(source_dir.glob("*.json"))
    if not candidates:
        return {}

    latest_file = candidates[-1]
    try:
        return json.loads(latest_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_latest_collected_data() -> Dict[str, Any]:
    """Load latest cached payloads from data/raw for scoring."""
    opensky = _read_latest_payload("opensky")
    aviationstack = _read_latest_payload("aviationstack")
    airlabs = _read_latest_payload("airlabs")

    opensky_records = int(opensky.get("records") or 0)
    aviationstack_records = int(aviationstack.get("records") or 0)
    airlabs_records = int(airlabs.get("records") or 0)

    total_live_records = opensky_records + aviationstack_records + airlabs_records
    # Saturate at 1.0 around 1000 live records to avoid oversized impact.
    live_traffic_index = min(total_live_records / 1000.0, 1.0)

    return {
        "opensky_records": opensky_records,
        "aviationstack_records": aviationstack_records,
        "airlabs_records": airlabs_records,
        "total_live_records": total_live_records,
        "live_traffic_index": live_traffic_index,
        "has_live_data": total_live_records > 0,
        "sources_used": [
            name
            for name, records in [
                ("opensky", opensky_records),
                ("aviationstack", aviationstack_records),
                ("airlabs", airlabs_records),
            ]
            if records > 0
        ],
    }


def _iter_latest_payloads(source: str, max_files: int = 20) -> List[Dict[str, Any]]:
    source_dir = RAW_DIR / source
    if not source_dir.exists():
        return []

    candidates = sorted(source_dir.glob("*.json"))[-max_files:]
    payloads: List[Dict[str, Any]] = []
    for file_path in candidates:
        try:
            payloads.append(json.loads(file_path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return payloads


def _extract_iata_pair(item: Any) -> str:
    if not isinstance(item, dict):
        return ""

    dep = (
        item.get("dep_iata")
        or (item.get("dep") or {}).get("iata")
        or (item.get("departure") or {}).get("iata")
        or ""
    )
    arr = (
        item.get("arr_iata")
        or (item.get("arr") or {}).get("iata")
        or (item.get("arrival") or {}).get("iata")
        or ""
    )

    dep_code = str(dep).strip().upper()
    arr_code = str(arr).strip().upper()
    if len(dep_code) == 3 and len(arr_code) == 3:
        return f"{dep_code}-{arr_code}"
    return ""


def _extract_airline_code(item: Any) -> str:
    if not isinstance(item, dict):
        return ""

    airline = item.get("airline") or {}
    code = (
        item.get("airline_iata")
        or airline.get("iata")
        or item.get("airline_icao")
        or airline.get("icao")
        or ""
    )
    code_text = str(code).strip().upper()
    if len(code_text) >= 2:
        return code_text[:2]
    return ""


def _parse_collected_at(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_dt_input(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_within_window(ts: datetime | None, period_start: datetime | None, period_end: datetime | None) -> bool:
    if ts is None:
        return False
    if period_start and ts < period_start:
        return False
    if period_end and ts >= period_end:
        return False
    return True


def build_route_heat_features(
    max_files: int = 20,
    hours_back: int = 24,
    period_start: Any = None,
    period_end: Any = None,
) -> Dict[str, Any]:
    """Build route-level heat from raw flight metadata (OD pair frequencies)."""
    od_counts: Counter[str] = Counter()
    airline_od_counts: Dict[str, Counter[str]] = {}
    start_dt = _parse_dt_input(period_start)
    end_dt = _parse_dt_input(period_end)
    if not start_dt and not end_dt:
        start_dt = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours_back)))
    payloads_used = 0

    for payload in _iter_latest_payloads("aviationstack", max_files=max_files):
        collected_at = _parse_collected_at(payload.get("collected_at"))
        if not _is_within_window(collected_at, start_dt, end_dt):
            continue
        payloads_used += 1
        aviationstack_data = payload.get("data") or {}
        flight_items = aviationstack_data.get("data") if isinstance(aviationstack_data, dict) else []
        for item in flight_items or []:
            od = _extract_iata_pair(item)
            if od:
                od_counts[od] += 1
                airline_code = _extract_airline_code(item)
                if airline_code:
                    airline_od_counts.setdefault(airline_code, Counter())
                    airline_od_counts[airline_code][od] += 1

    for payload in _iter_latest_payloads("airlabs", max_files=max_files):
        collected_at = _parse_collected_at(payload.get("collected_at"))
        if not _is_within_window(collected_at, start_dt, end_dt):
            continue
        payloads_used += 1
        for item in payload.get("response") or []:
            od = _extract_iata_pair(item)
            if od:
                od_counts[od] += 1
                airline_code = _extract_airline_code(item)
                if airline_code:
                    airline_od_counts.setdefault(airline_code, Counter())
                    airline_od_counts[airline_code][od] += 1

    max_count = max(od_counts.values(), default=0)
    if max_count > 0:
        od_heat = {od: count / max_count for od, count in od_counts.items()}
    else:
        od_heat = {}

    od_airlines: Dict[str, List[str]] = {}
    for airline_code, counts in airline_od_counts.items():
        for od in counts:
            od_airlines.setdefault(od, []).append(airline_code)

    airline_od_counts_serializable = {
        airline_code: dict(counts)
        for airline_code, counts in airline_od_counts.items()
    }
    od_airline_counts = {od: len(set(codes)) for od, codes in od_airlines.items()}
    od_airlines = {od: sorted(set(codes)) for od, codes in od_airlines.items()}

    return {
        "od_counts": dict(od_counts),
        "od_heat": od_heat,
        "airline_od_counts": airline_od_counts_serializable,
        "od_airline_counts": od_airline_counts,
        "od_airlines": od_airlines,
        "route_obs_total": int(sum(od_counts.values())),
        "route_obs_unique": len(od_counts),
        "route_heat_window_hours": int(hours_back),
        "route_heat_window_start": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if start_dt else "",
        "route_heat_window_end": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if end_dt else "",
        "route_heat_payloads_used": payloads_used,
        "route_heat_sources": [
            name
            for name in ["aviationstack", "airlabs"]
            if (RAW_DIR / name).exists()
        ],
    }


def load_opensky_flights_od_data(region: str) -> Dict[str, Any]:
    """
    Load the latest opensky_flights collection for *region*.
    Returns a dict with keys:
      od_heat_realtime  – {od: normalised_frequency, ...}
      od_raw_counts     – {airline: {od: count}, ...}
      records           – total unique OD pairs found
      data_age_hours    – how old the file is (0 if unknown)
    """
    source_dir = RAW_DIR / "opensky_flights"
    if not source_dir.exists():
        return {}

    def _is_non_empty(payload: Dict[str, Any]) -> bool:
        od_counts = payload.get("od_counts") or {}
        if any(bool(v) for v in od_counts.values()):
            return True
        return int(payload.get("raw_records") or 0) > 0 or int(payload.get("records") or 0) > 0

    # Prefer the most recent non-empty file that matches this region
    candidates = sorted(source_dir.glob("*.json"))
    matched = None
    for path in reversed(candidates):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("region") == region and _is_non_empty(payload):
                matched = payload
                break
        except Exception:
            continue

    if matched is None:
        # No non-empty region-specific file: fall back to the latest non-empty file regardless of region.
        for path in reversed(candidates):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if _is_non_empty(payload):
                    matched = payload
                    break
            except Exception:
                continue

    if not matched:
        return {}

    od_counts_by_airline: Dict[str, Dict[str, int]] = matched.get("od_counts") or {}

    # Aggregate across airlines to get overall OD frequency
    global_od: Dict[str, int] = {}
    for airline_ods in od_counts_by_airline.values():
        for od, cnt in airline_ods.items():
            global_od[od] = global_od.get(od, 0) + cnt

    max_cnt = max(global_od.values(), default=0)
    od_heat_realtime = (
        {od: cnt / max_cnt for od, cnt in global_od.items()} if max_cnt > 0 else {}
    )

    # Work out data age
    from datetime import datetime, timezone
    data_age_hours = 0.0
    collected_str = matched.get("collected_at", "")
    if collected_str:
        try:
            dt = datetime.strptime(collected_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            data_age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
        except Exception:
            pass

    return {
        "od_heat_realtime": od_heat_realtime,
        "od_raw_counts": od_counts_by_airline,
        "records": len(global_od),
        "raw_records": int(matched.get("raw_records", 0)),
        "data_age_hours": round(data_age_hours, 1),
        "begin_epoch": matched.get("begin_epoch"),
        "end_epoch": matched.get("end_epoch"),
        "region": matched.get("region", ""),
        "hubs_queried": matched.get("hubs_queried", []),
        "errors": matched.get("errors", []),
    }


# Seasonal demand multipliers: (region -> month -> boost added to demand_score)
# Positive = peak season, negative = off-peak. Values represent additive adjustment.
_SEASONAL = {
    "Europe":        {6: 0.07, 7: 0.10, 8: 0.08, 12: 0.05, 1: -0.04, 2: -0.03},
    "Asia":          {1: 0.06, 2: 0.09, 10: 0.05, 11: 0.04, 7: -0.03, 8: -0.02},
    "North America": {7: 0.08, 8: 0.07, 11: 0.05, 12: 0.06, 2: -0.04, 3: -0.02},
    "South America": {1: 0.07, 7: 0.06, 12: 0.05, 6: -0.03, 4: -0.02},
    "Africa":        {12: 0.06, 1: 0.07, 7: 0.04, 4: -0.03, 5: -0.02},
    "Oceania":       {12: 0.08, 1: 0.07, 7: -0.04, 8: -0.03, 4: 0.03},
}

_SEASONAL_PHASE = {
    "Europe": 0,
    "Asia": 2,
    "North America": 4,
    "South America": 6,
    "Africa": 8,
    "Oceania": 10,
    "Global": 0,
}


def calculate_route_scores(
    collected_data: Dict[str, Any],
    airline_code: str = "AF",
    num_recommendations: int = 3,
) -> List[RouteScore]:
    """
    Score all European OD routes based on collected market data.
    
    Scoring factors:
    1. Demand indicator (search volume, flight frequency proxies)
    2. Price level (attractive pricing window)
    3. Competitive intensity (lower = better opportunity)
    4. Distance (operational efficiency)
    """
    
    scores = []
    selected_region = str(collected_data.get("selected_region") or "Europe")
    analysis_month = int(collected_data.get("analysis_month") or 0)
    seasonal_map = _SEASONAL.get(selected_region, {})
    # Region-level seasonality (same for all routes in this region/month)
    phase = _SEASONAL_PHASE.get(selected_region, 0)
    if 1 <= analysis_month <= 12:
        seasonal_wave = 0.04 * math.sin((2 * math.pi * (analysis_month + phase)) / 12.0)
    else:
        seasonal_wave = 0.0
    regional_seasonal_boost = seasonal_map.get(analysis_month, 0.0) + seasonal_wave

    routes = get_od_by_airline_homebase(airline_code, selected_region)
    # Hard safety guard: never allow cross-region routes in the final candidate set.
    if selected_region != "Global":
        region_od_set = {r["od"] for r in get_routes_by_region(selected_region)}
        routes = [r for r in routes if r["od"] in region_od_set]

    live_idx = float(collected_data.get("live_traffic_index") or 0.0)
    od_heat = collected_data.get("od_heat") or {}
    has_route_obs = bool(collected_data.get("route_obs_total"))

    # Augment with real OpenSky flights OD frequency (overrides estimates when available)
    flights_data = load_opensky_flights_od_data(selected_region)
    od_heat_realtime: Dict[str, float] = flights_data.get("od_heat_realtime") or {}
    historical_od_counts_by_airline: Dict[str, Dict[str, int]] = flights_data.get("od_raw_counts") or {}
    has_realtime_od = bool(od_heat_realtime)
    # Merge: realtime takes precedence; fall back to aviationstack/airlabs heat
    if has_realtime_od:
        merged_od_heat = {**od_heat, **od_heat_realtime}  # realtime overwrites
    else:
        merged_od_heat = od_heat

    live_od_airlines: Dict[str, List[str]] = collected_data.get("od_airlines") or {}
    live_od_counts_by_airline: Dict[str, Dict[str, int]] = collected_data.get("airline_od_counts") or {}
    historical_od_airlines: Dict[str, set[str]] = {}
    for observed_airline, airline_od_counts in historical_od_counts_by_airline.items():
        observed_airline_code = str(observed_airline).strip().upper()
        if len(observed_airline_code) < 2:
            continue
        for od in airline_od_counts:
            historical_od_airlines.setdefault(od, set()).add(observed_airline_code[:2])

    tier_prior = {"high": 0.8, "medium": 0.5, "low": 0.2}

    for route in routes:
        od = route["od"]

        # Route-level seasonality: each OD has a distinct month response curve.
        # This avoids "all scores move together" and allows rankings to change by month.
        if 1 <= analysis_month <= 12:
            od_phase = (sum(ord(ch) for ch in od) % 12)
            route_seasonal_boost = 0.30 * math.sin((2 * math.pi * (analysis_month + od_phase)) / 12.0)
        else:
            route_seasonal_boost = 0.0

        homebase = get_homebase_for_airline(airline_code)
        touches_homebase = bool(homebase and homebase in [od[:3], od[4:7]])
        homebase_affinity_boost = 0.22 if touches_homebase else -0.05
        network_fit_score = 1.0 if touches_homebase else 0.45
        
        # Factor 1: Demand proxy (route heat + tier prior + regional heat + seasonal)
        tier_score = tier_prior.get(route["demand_tier"], 0.3)
        route_heat = float(merged_od_heat.get(od, 0.0))
        observed_airlines = set(live_od_airlines.get(od, [])) | historical_od_airlines.get(od, set())
        target_airline_present = airline_code in observed_airlines
        competitor_count = len(observed_airlines - {airline_code})
        target_airline_live_count = int((live_od_counts_by_airline.get(airline_code) or {}).get(od, 0))
        target_airline_historical_count = int((historical_od_counts_by_airline.get(airline_code) or {}).get(od, 0))
        target_airline_observed_flights = target_airline_live_count + target_airline_historical_count
        has_observed_support = od in merged_od_heat or bool(observed_airlines) or target_airline_observed_flights > 0
        if not has_observed_support:
            continue
        heat_source = "realtime" if has_realtime_od and od in od_heat_realtime else \
                      "observed" if has_route_obs else "fallback"
        if heat_source == "fallback":
            # No real data available – estimate from demand tier
            route_heat = tier_score * 0.7
        demand_score = min(
            max(
                0.48 * tier_score
                + 0.32 * route_heat
                + 0.08 * live_idx
                + regional_seasonal_boost
                + route_seasonal_boost,
                0.0,
            ),
            1.0,
        )
        
        # Factor 2: Price attractiveness proxy
        # Medium-haul routes are often a good balance between yield and utilization.
        distance = route["distance_km"]
        if 500 <= distance <= 1600:
            price_score = 0.82
        elif 300 <= distance < 500 or 1600 < distance <= 2200:
            price_score = 0.68
        else:
            price_score = 0.52

        seasonality_score = min(max(0.5 + regional_seasonal_boost + route_seasonal_boost, 0.0), 1.0)
        
        # Factor 3: Airline-aware market opportunity.
        # Interprets the observed market structure instead of only subtracting generic traffic heat.
        entry_whitespace_score = max(0.20, 0.92 - 0.14 * competitor_count)
        incumbent_presence_strength = min(target_airline_observed_flights / 80.0, 1.0)
        if target_airline_present:
            market_opportunity_score = max(
                0.18,
                min(
                    0.95,
                    0.52
                    + 0.18 * tier_score
                    + 0.12 * route_heat
                    + 0.08 * seasonality_score
                    - 0.07 * competitor_count
                    - 0.18 * incumbent_presence_strength,
                )
            )
        elif observed_airlines:
            market_opportunity_score = min(
                0.98,
                0.40 + 0.28 * route_heat + 0.18 * tier_score + 0.22 * entry_whitespace_score
            )
        else:
            market_opportunity_score = min(0.90, 0.34 + 0.24 * tier_score + 0.18 * route_heat)

        competition_score = market_opportunity_score

        if target_airline_present and competitor_count >= 4:
            market_opportunity_label = "defend-or-upgauge"
        elif target_airline_present:
            market_opportunity_label = "incumbent-growth"
        elif observed_airlines:
            market_opportunity_label = "new-entry"
        else:
            market_opportunity_label = "white-space"

        # Deterministic route-level adjustment so equal tiers do not collapse to same score.
        route_signature = (sum(ord(ch) for ch in od) % 9) / 100.0
        
        # Factor 4: Distance efficiency (sweet spot 300-2000 km)
        if 300 <= distance <= 2000:
            distance_score = 1.0
        elif 200 <= distance <= 2500:
            distance_score = 0.8
        else:
            distance_score = 0.5
        
        # Weighted combination
        total_score = (
            demand_score * 0.30 +
            price_score * 0.24 +
            competition_score * 0.16 +
            distance_score * 0.10 +
            network_fit_score * 0.12 +
            seasonality_score * 0.08
        )
        total_score += homebase_affinity_boost
        total_score = min(max(total_score + route_signature, 0.0), 1.0)
        
        # Estimate PAX (simulated based on demand tier and distance)
        # In real scenario, use Estimated_Pax = Seats_total * predicted_LF
        estimated_pax_map = {
            "high": {"short": 200, "medium": 180, "long": 160},
            "medium": {"short": 150, "medium": 130, "long": 110},
            "low": {"short": 100, "medium": 80, "long": 60},
        }
        
        if distance < 500:
            category = "short"
        elif distance < 1200:
            category = "medium"
        else:
            category = "long"
        
        estimated_pax = int(estimated_pax_map[route["demand_tier"]][category] * (0.9 + 0.4 * live_idx))
        aircraft = recommend_aircraft(estimated_pax, airline_code=airline_code)
        
        reasoning = [
            f"[rule-based] Demand tier: {route['demand_tier'].upper()}",
            f"[rule-based] Distance: {distance} km (efficient)",
            f"[observed] Regional heat index: {live_idx:.2f}",
            f"[observed:{heat_source}] Route heat: {route_heat:.2f}",
            f"[observed] OD airlines seen: {len(observed_airlines)} total, {competitor_count} competitor(s)",
            f"[observed] Target airline on OD: {'YES' if target_airline_present else 'NO'}",
            f"[observed] Target airline flights seen: {target_airline_observed_flights}",
            f"[model-based] Market opportunity: {market_opportunity_label} ({market_opportunity_score:.2f})",
            f"[model-based] Seasonality fit: {seasonality_score:.2f}",
            f"[rule-based] Homebase affinity: {'YES' if touches_homebase else 'NO'}",
            f"[model-based] Est. PAX: {estimated_pax} -> {aircraft}",
        ]
        
        scores.append(
            RouteScore(
                od=od,
                origin=route["origin"],
                destination=route["destination"],
                score=total_score,
                estimated_pax=estimated_pax,
                recommended_aircraft=aircraft,
                observed_airlines_total=len(observed_airlines),
                observed_airlines=sorted(observed_airlines),
                competitor_count=competitor_count,
                target_airline_present=target_airline_present,
                target_airline_observed_flights=target_airline_observed_flights,
                market_opportunity_score=market_opportunity_score,
                market_opportunity_label=market_opportunity_label,
                reasoning=reasoning,
            )
        )
    
    # Sort by score and return top N
    sorted_scores = sorted(scores, key=lambda x: x.score, reverse=True)
    return sorted_scores[:num_recommendations]


def generate_recommendation_report(routes: List[RouteScore]) -> Dict[str, Any]:
    """Format recommendation for display."""
    return {
        "recommendations": [
            {
                "rank": i + 1,
                "od": r.od,
                "route": f"{r.origin} → {r.destination}",
                "score": round(r.score, 3),
                "estimated_pax": r.estimated_pax,
                "aircraft": r.recommended_aircraft,
                "observed_airlines_total": r.observed_airlines_total,
                "observed_airlines": r.observed_airlines,
                "competitor_count": r.competitor_count,
                "target_airline_present": r.target_airline_present,
                "target_airline_observed_flights": r.target_airline_observed_flights,
                "market_opportunity_score": round(r.market_opportunity_score, 3),
                "market_opportunity_label": r.market_opportunity_label,
                "rationale": " | ".join(r.reasoning),
            }
            for i, r in enumerate(routes)
        ]
    }
