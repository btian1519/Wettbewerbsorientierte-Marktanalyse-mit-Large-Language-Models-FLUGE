import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FR24_SNAPSHOT_CSV = PROCESSED_DIR / "fr24_flight_snapshot.csv"
sys.path.insert(0, str(BASE_DIR))

from src.route_database import get_aircraft_seat_capacity, get_all_od_routes, get_homebases_for_airline


def parse_collected_at(value: Any) -> datetime:
    text = str(value or "").strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    raise ValueError(f"Unsupported timestamp format: {value!r}")


def load_json_files(source: str) -> List[Dict[str, Any]]:
    source_dir = RAW_DIR / source
    if not source_dir.exists():
        return []

    payloads: List[Dict[str, Any]] = []
    for path in sorted(source_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_file_path"] = str(path)
            payloads.append(payload)
        except Exception:
            continue
    return payloads


def build_route_lookup() -> Dict[str, Dict[str, Any]]:
    route_lookup: Dict[str, Dict[str, Any]] = {}
    for route in get_all_od_routes():
        route_lookup[str(route.get("od") or "")] = route
    return route_lookup


def build_check24_lookup() -> Dict[str, List[Dict[str, Any]]]:
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for payload in load_json_files("check24"):
        query = payload.get("query") or {}
        origin = str(query.get("origin") or "").strip().upper()
        destination = str(query.get("destination") or "").strip().upper()
        od = f"{origin}-{destination}" if origin and destination else ""
        if not od:
            continue
        payload["_collected_dt"] = parse_collected_at(payload.get("collected_at"))
        lookup.setdefault(od, []).append(payload)

    for od in lookup:
        lookup[od].sort(key=lambda item: item["_collected_dt"])
    return lookup


def build_aviationstack_lookup() -> Dict[str, List[Dict[str, Any]]]:
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for payload in load_json_files("aviationstack"):
        try:
            collected_dt = parse_collected_at(payload.get("collected_at"))
        except Exception:
            continue
        records = _extract_aviationstack_records(payload)
        route_counts: Dict[str, int] = {}
        route_airlines: Dict[str, set[str]] = {}
        airline_route_counts: Dict[str, Dict[str, int]] = {}
        route_departure_hours: Dict[str, List[int]] = {}
        route_scheduled_counts: Dict[str, int] = {}
        for record in records:
            departure = record.get("departure") or {}
            arrival = record.get("arrival") or {}
            airline = record.get("airline") or {}
            dep_iata = str(departure.get("iata") or "").strip().upper()
            arr_iata = str(arrival.get("iata") or "").strip().upper()
            airline_iata = str(airline.get("iata") or "").strip().upper()
            if len(dep_iata) != 3 or len(arr_iata) != 3:
                continue
            od = f"{dep_iata}-{arr_iata}"
            route_counts[od] = route_counts.get(od, 0) + 1
            if airline_iata:
                route_airlines.setdefault(od, set()).add(airline_iata)
                airline_route_counts.setdefault(airline_iata, {})
                airline_route_counts[airline_iata][od] = airline_route_counts[airline_iata].get(od, 0) + 1
            scheduled_text = str(departure.get("scheduled") or "").strip()
            if scheduled_text:
                try:
                    route_departure_hours.setdefault(od, []).append(datetime.fromisoformat(scheduled_text.replace("Z", "+00:00")).hour)
                except ValueError:
                    pass
            if str(record.get("flight_status") or "").strip().lower() == "scheduled":
                route_scheduled_counts[od] = route_scheduled_counts.get(od, 0) + 1

        lookup_payload = {
            "_collected_dt": collected_dt,
            "route_counts": route_counts,
            "route_airlines": {od: sorted(values) for od, values in route_airlines.items()},
            "airline_route_counts": airline_route_counts,
            "route_departure_hour_avg": {
                od: round(sum(hours) / len(hours), 2) for od, hours in route_departure_hours.items() if hours
            },
            "route_scheduled_share": {
                od: round(route_scheduled_counts.get(od, 0) / count, 4) if count else 0.0
                for od, count in route_counts.items()
            },
        }
        lookup.setdefault("all", []).append(lookup_payload)

    lookup["all"] = sorted(lookup.get("all", []), key=lambda item: item["_collected_dt"])
    return lookup


def _extract_aviationstack_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data") or {}
    records = data.get("data") or []
    return [record for record in records if isinstance(record, dict)]


def build_airlabs_lookup() -> Dict[str, List[Dict[str, Any]]]:
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for payload in load_json_files("airlabs"):
        try:
            collected_dt = parse_collected_at(payload.get("collected_at"))
        except Exception:
            continue
        data = payload.get("data") or {}
        records = data.get("response") or []
        route_counts: Dict[str, int] = {}
        route_airlines: Dict[str, set[str]] = {}
        airline_route_counts: Dict[str, Dict[str, int]] = {}
        route_speeds: Dict[str, List[float]] = {}
        route_aircraft_types: Dict[str, set[str]] = {}
        route_seat_values: Dict[str, List[int]] = {}
        airline_route_seat_values: Dict[str, Dict[str, List[int]]] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            dep_iata = str(record.get("dep_iata") or "").strip().upper()
            arr_iata = str(record.get("arr_iata") or "").strip().upper()
            airline_iata = str(record.get("airline_iata") or "").strip().upper()
            aircraft_icao = str(record.get("aircraft_icao") or "").strip().upper()
            if len(dep_iata) != 3 or len(arr_iata) != 3:
                continue
            od = f"{dep_iata}-{arr_iata}"
            route_counts[od] = route_counts.get(od, 0) + 1
            if airline_iata:
                route_airlines.setdefault(od, set()).add(airline_iata)
                airline_route_counts.setdefault(airline_iata, {})
                airline_route_counts[airline_iata][od] = airline_route_counts[airline_iata].get(od, 0) + 1
            speed = float(record.get("speed") or 0.0)
            if speed > 0:
                route_speeds.setdefault(od, []).append(speed)
            if aircraft_icao:
                route_aircraft_types.setdefault(od, set()).add(aircraft_icao)
                seat_capacity = get_aircraft_seat_capacity(aircraft_icao)
                if seat_capacity > 0:
                    route_seat_values.setdefault(od, []).append(seat_capacity)
                    if airline_iata:
                        airline_route_seat_values.setdefault(airline_iata, {})
                        airline_route_seat_values[airline_iata].setdefault(od, []).append(seat_capacity)

        lookup_payload = {
            "_collected_dt": collected_dt,
            "route_counts": route_counts,
            "route_airlines": {od: sorted(values) for od, values in route_airlines.items()},
            "airline_route_counts": airline_route_counts,
            "route_avg_speed": {
                od: round(sum(speeds) / len(speeds), 2) for od, speeds in route_speeds.items() if speeds
            },
            "route_aircraft_type_count": {
                od: len(types) for od, types in route_aircraft_types.items()
            },
            "route_avg_seats": {
                od: round(sum(seats) / len(seats), 2) for od, seats in route_seat_values.items() if seats
            },
            "route_total_capacity_proxy": {
                od: int(sum(seats)) for od, seats in route_seat_values.items() if seats
            },
            "airline_route_avg_seats": {
                airline: {
                    od: round(sum(seats) / len(seats), 2) for od, seats in od_map.items() if seats
                }
                for airline, od_map in airline_route_seat_values.items()
            },
        }
        lookup.setdefault("all", []).append(lookup_payload)

    lookup["all"] = sorted(lookup.get("all", []), key=lambda item: item["_collected_dt"])
    return lookup


def _first_non_empty(mapping: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(mapping.get(key) or "").strip()
        if value:
            return value
    return ""


def _normalize_fr24_row(row: Dict[str, Any]) -> Dict[str, Any] | None:
    lower = {str(key).strip().lower(): value for key, value in row.items()}
    collected_text = _first_non_empty(
        lower,
        "snapshot_at",
        "collected_at",
        "observed_at",
        "flight_date",
        "date",
    )
    if not collected_text:
        return None
    try:
        collected_dt = parse_collected_at(collected_text)
    except ValueError:
        return None

    origin = _first_non_empty(lower, "origin", "origin_iata", "dep_iata", "from", "departure_iata").upper()
    destination = _first_non_empty(lower, "destination", "destination_iata", "arr_iata", "to", "arrival_iata").upper()
    if len(origin) != 3 or len(destination) != 3:
        return None

    airline = _first_non_empty(lower, "airline_iata", "carrier_iata", "operator_iata", "airline", "carrier").upper()
    aircraft = _first_non_empty(lower, "aircraft_icao", "aircraft_type", "aircraft", "equipment").upper()
    seat_capacity = 0.0
    seat_text = _first_non_empty(lower, "seat_capacity", "seats", "aircraft_seats")
    if seat_text:
        try:
            seat_capacity = float(seat_text)
        except ValueError:
            seat_capacity = 0.0
    if seat_capacity <= 0 and aircraft:
        seat_capacity = float(get_aircraft_seat_capacity(aircraft))

    return {
        "_collected_dt": collected_dt,
        "od": f"{origin}-{destination}",
        "airline": airline,
        "aircraft": aircraft,
        "seat_capacity": seat_capacity,
    }


def build_fr24_lookup() -> Dict[str, List[Dict[str, Any]]]:
    lookup: Dict[str, List[Dict[str, Any]]] = {"all": []}
    if not FR24_SNAPSHOT_CSV.exists():
        return lookup

    grouped_records: Dict[datetime, List[Dict[str, Any]]] = {}
    with FR24_SNAPSHOT_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = _normalize_fr24_row(row)
            if normalized is None:
                continue
            grouped_records.setdefault(normalized["_collected_dt"], []).append(normalized)

    for collected_dt in sorted(grouped_records):
        route_counts: Dict[str, int] = {}
        route_airlines: Dict[str, set[str]] = {}
        airline_route_counts: Dict[str, Dict[str, int]] = {}
        route_aircraft_types: Dict[str, set[str]] = {}
        route_seat_values: Dict[str, List[float]] = {}
        airline_route_seat_values: Dict[str, Dict[str, List[float]]] = {}
        for record in grouped_records[collected_dt]:
            od = str(record.get("od") or "")
            airline = str(record.get("airline") or "")
            aircraft = str(record.get("aircraft") or "")
            seat_capacity = float(record.get("seat_capacity") or 0.0)
            if not od:
                continue
            route_counts[od] = route_counts.get(od, 0) + 1
            if airline:
                route_airlines.setdefault(od, set()).add(airline)
                airline_route_counts.setdefault(airline, {})
                airline_route_counts[airline][od] = airline_route_counts[airline].get(od, 0) + 1
            if aircraft:
                route_aircraft_types.setdefault(od, set()).add(aircraft)
            if seat_capacity > 0:
                route_seat_values.setdefault(od, []).append(seat_capacity)
                if airline:
                    airline_route_seat_values.setdefault(airline, {})
                    airline_route_seat_values[airline].setdefault(od, []).append(seat_capacity)

        lookup["all"].append(
            {
                "_collected_dt": collected_dt,
                "route_counts": route_counts,
                "route_airlines": {od: sorted(values) for od, values in route_airlines.items()},
                "airline_route_counts": airline_route_counts,
                "route_aircraft_type_count": {od: len(types) for od, types in route_aircraft_types.items()},
                "route_avg_seats": {
                    od: round(sum(seats) / len(seats), 2) for od, seats in route_seat_values.items() if seats
                },
                "route_total_capacity_proxy": {
                    od: int(round(sum(seats))) for od, seats in route_seat_values.items() if seats
                },
                "airline_route_avg_seats": {
                    airline: {
                        od: round(sum(seats) / len(seats), 2) for od, seats in od_map.items() if seats
                    }
                    for airline, od_map in airline_route_seat_values.items()
                },
            }
        )
    return lookup


def get_latest_aviationstack_features(
    od: str,
    airline_code: str,
    snapshot_dt: datetime,
    aviationstack_lookup: Dict[str, List[Dict[str, Any]]],
    max_age_hours: float,
) -> Dict[str, Any]:
    payload = select_nearest_snapshot(
        aviationstack_lookup.get("all", []),
        snapshot_dt,
        max_age_hours=max_age_hours,
    )
    if payload is None:
        return {
            "aviationstack_route_records": 0,
            "aviationstack_route_airline_count": 0,
            "aviationstack_target_airline_records": 0,
            "aviationstack_target_airline_present": 0,
            "aviationstack_route_departure_hour_avg": 0.0,
            "aviationstack_route_scheduled_share": 0.0,
        }
    route_counts = payload.get("route_counts") or {}
    route_airlines = payload.get("route_airlines") or {}
    airline_route_counts = payload.get("airline_route_counts") or {}
    route_departure_hour_avg = payload.get("route_departure_hour_avg") or {}
    route_scheduled_share = payload.get("route_scheduled_share") or {}
    target_airline_records = int((airline_route_counts.get(airline_code) or {}).get(od, 0) or 0)
    return {
        "aviationstack_route_records": int(route_counts.get(od) or 0),
        "aviationstack_route_airline_count": len(route_airlines.get(od) or []),
        "aviationstack_target_airline_records": target_airline_records,
        "aviationstack_target_airline_present": int(target_airline_records > 0),
        "aviationstack_route_departure_hour_avg": float(route_departure_hour_avg.get(od) or 0.0),
        "aviationstack_route_scheduled_share": float(route_scheduled_share.get(od) or 0.0),
    }


def get_latest_airlabs_features(
    od: str,
    airline_code: str,
    snapshot_dt: datetime,
    airlabs_lookup: Dict[str, List[Dict[str, Any]]],
    max_age_hours: float,
) -> Dict[str, Any]:
    payload = select_nearest_snapshot(
        airlabs_lookup.get("all", []),
        snapshot_dt,
        max_age_hours=max_age_hours,
    )
    if payload is None:
        return {
            "airlabs_route_records": 0,
            "airlabs_route_airline_count": 0,
            "airlabs_target_airline_records": 0,
            "airlabs_target_airline_present": 0,
            "airlabs_route_avg_speed": 0.0,
            "airlabs_route_aircraft_type_count": 0,
            "airlabs_route_avg_seats": 0.0,
            "airlabs_route_total_capacity_proxy": 0.0,
            "airlabs_target_airline_avg_seats": 0.0,
        }
    route_counts = payload.get("route_counts") or {}
    route_airlines = payload.get("route_airlines") or {}
    airline_route_counts = payload.get("airline_route_counts") or {}
    route_avg_speed = payload.get("route_avg_speed") or {}
    route_aircraft_type_count = payload.get("route_aircraft_type_count") or {}
    route_avg_seats = payload.get("route_avg_seats") or {}
    route_total_capacity_proxy = payload.get("route_total_capacity_proxy") or {}
    airline_route_avg_seats = payload.get("airline_route_avg_seats") or {}
    target_airline_records = int((airline_route_counts.get(airline_code) or {}).get(od, 0) or 0)
    return {
        "airlabs_route_records": int(route_counts.get(od) or 0),
        "airlabs_route_airline_count": len(route_airlines.get(od) or []),
        "airlabs_target_airline_records": target_airline_records,
        "airlabs_target_airline_present": int(target_airline_records > 0),
        "airlabs_route_avg_speed": float(route_avg_speed.get(od) or 0.0),
        "airlabs_route_aircraft_type_count": int(route_aircraft_type_count.get(od) or 0),
        "airlabs_route_avg_seats": float(route_avg_seats.get(od) or 0.0),
        "airlabs_route_total_capacity_proxy": float(route_total_capacity_proxy.get(od) or 0.0),
        "airlabs_target_airline_avg_seats": float(((airline_route_avg_seats.get(airline_code) or {}).get(od)) or 0.0),
    }


def get_latest_check24_features(
    od: str,
    snapshot_dt: datetime,
    check24_lookup: Dict[str, List[Dict[str, Any]]],
    max_age_hours: float,
) -> Dict[str, Any]:
    payload = select_nearest_snapshot(
        check24_lookup.get(od, []),
        snapshot_dt,
        max_age_hours=max_age_hours,
    )
    if payload is None:
        return {
            "check24_records": 0,
            "check24_direct_count": 0,
            "check24_direct_min_price_eur": 0.0,
            "check24_offer_min_price_eur": 0.0,
            "check24_offer_avg_price_eur": 0.0,
            "check24_direct_offer_share": 0.0,
            "check24_offer_lead_time_days": 0,
            "check24_snapshot_age_hours": 0.0,
        }

    offers = payload.get("offers") or []
    prices = [float(item.get("price_eur") or 0.0) for item in offers if float(item.get("price_eur") or 0.0) > 0]
    direct_offer_count = sum(1 for item in offers if any(str(stop).strip().lower() == "direkt" for stop in (item.get("stops") or [])))
    summary = payload.get("summary") or {}
    query = payload.get("query") or {}
    direct_text = str(summary.get("direct_count") or "0").strip()
    direct_min_price_text = str(summary.get("direct_min_price") or "").replace("Ab", "").strip()
    direct_min_price_eur = _parse_eur_amount(direct_min_price_text)
    lead_time_days = 0
    departure_date = str(query.get("departure_date") or "").strip()
    if departure_date:
        try:
            lead_time_days = int((datetime.fromisoformat(departure_date).date() - payload["_collected_dt"].date()).days)
        except ValueError:
            lead_time_days = 0
    snapshot_age_hours = round(abs((payload["_collected_dt"] - snapshot_dt).total_seconds()) / 3600.0, 2)

    return {
        "check24_records": int(payload.get("records") or 0),
        "check24_direct_count": int(direct_text) if direct_text.isdigit() else 0,
        "check24_direct_min_price_eur": direct_min_price_eur,
        "check24_offer_min_price_eur": min(prices) if prices else 0.0,
        "check24_offer_avg_price_eur": round(sum(prices) / len(prices), 2) if prices else 0.0,
        "check24_direct_offer_share": round(direct_offer_count / len(offers), 4) if offers else 0.0,
        "check24_offer_lead_time_days": lead_time_days,
        "check24_snapshot_age_hours": snapshot_age_hours,
    }


def get_latest_fr24_features(
    od: str,
    airline_code: str,
    snapshot_dt: datetime,
    fr24_lookup: Dict[str, List[Dict[str, Any]]],
    max_age_hours: float,
) -> Dict[str, Any]:
    payload = select_nearest_snapshot(
        fr24_lookup.get("all", []),
        snapshot_dt,
        max_age_hours=max_age_hours,
    )
    if payload is None:
        return {
            "fr24_route_records": 0,
            "fr24_route_airline_count": 0,
            "fr24_target_airline_records": 0,
            "fr24_target_airline_present": 0,
            "fr24_route_aircraft_type_count": 0,
            "fr24_route_avg_seats": 0.0,
            "fr24_route_total_capacity_proxy": 0.0,
            "fr24_target_airline_avg_seats": 0.0,
        }
    route_counts = payload.get("route_counts") or {}
    route_airlines = payload.get("route_airlines") or {}
    airline_route_counts = payload.get("airline_route_counts") or {}
    route_aircraft_type_count = payload.get("route_aircraft_type_count") or {}
    route_avg_seats = payload.get("route_avg_seats") or {}
    route_total_capacity_proxy = payload.get("route_total_capacity_proxy") or {}
    airline_route_avg_seats = payload.get("airline_route_avg_seats") or {}
    target_airline_records = int((airline_route_counts.get(airline_code) or {}).get(od, 0) or 0)
    return {
        "fr24_route_records": int(route_counts.get(od) or 0),
        "fr24_route_airline_count": len(route_airlines.get(od) or []),
        "fr24_target_airline_records": target_airline_records,
        "fr24_target_airline_present": int(target_airline_records > 0),
        "fr24_route_aircraft_type_count": int(route_aircraft_type_count.get(od) or 0),
        "fr24_route_avg_seats": float(route_avg_seats.get(od) or 0.0),
        "fr24_route_total_capacity_proxy": float(route_total_capacity_proxy.get(od) or 0.0),
        "fr24_target_airline_avg_seats": float(((airline_route_avg_seats.get(airline_code) or {}).get(od)) or 0.0),
    }


def _parse_eur_amount(value: str) -> float:
    text = str(value or "").replace("\xa0", " ").replace("€", "").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def compute_price_distance_proxy(price_eur: float, distance_km: int) -> float:
    if price_eur <= 0 or distance_km <= 0:
        return 0.0
    return round((price_eur / distance_km) * 1000.0, 2)


def select_nearest_snapshot(
    snapshots: List[Dict[str, Any]],
    anchor_dt: datetime,
    max_age_hours: float,
) -> Dict[str, Any] | None:
    if not snapshots:
        return None

    max_delta = timedelta(hours=max_age_hours) if max_age_hours > 0 else None
    best_payload: Dict[str, Any] | None = None
    best_key: tuple[float, float] | None = None
    for payload in snapshots:
        collected_dt = payload.get("_collected_dt")
        if not isinstance(collected_dt, datetime):
            continue
        delta = abs(collected_dt - anchor_dt)
        if max_delta is not None and delta > max_delta:
            continue
        # Prefer the nearest snapshot; break ties toward earlier observations.
        tie_break = 0.0 if collected_dt <= anchor_dt else 1.0
        ranking_key = (delta.total_seconds(), tie_break)
        if best_key is None or ranking_key < best_key:
            best_key = ranking_key
            best_payload = payload
    return best_payload


def build_rows(aux_window_hours: float = 24.0, check24_window_hours: float = 336.0) -> List[Dict[str, Any]]:
    route_lookup = build_route_lookup()
    check24_lookup = build_check24_lookup()
    aviationstack_lookup = build_aviationstack_lookup()
    airlabs_lookup = build_airlabs_lookup()
    fr24_lookup = build_fr24_lookup()
    opensky_payloads = [payload for payload in load_json_files("opensky_flights") if payload.get("region")]

    grouped_by_region: Dict[str, List[Dict[str, Any]]] = {}
    for payload in opensky_payloads:
        try:
            payload["_collected_dt"] = parse_collected_at(payload.get("collected_at"))
        except Exception:
            continue
        grouped_by_region.setdefault(str(payload.get("region")), []).append(payload)

    rows: List[Dict[str, Any]] = []
    for region, payloads in grouped_by_region.items():
        payloads.sort(key=lambda item: item["_collected_dt"])
        for index, payload in enumerate(payloads[:-1]):
            next_payload = payloads[index + 1]
            current_dt = payload["_collected_dt"]
            next_dt = next_payload["_collected_dt"]
            current_counts_by_airline: Dict[str, Dict[str, int]] = payload.get("od_counts") or {}
            next_counts_by_airline: Dict[str, Dict[str, int]] = next_payload.get("od_counts") or {}

            current_global_od: Dict[str, int] = {}
            next_global_od: Dict[str, int] = {}
            current_airlines_per_od: Dict[str, set[str]] = {}
            for airline, od_counts in current_counts_by_airline.items():
                airline_code = str(airline or "").strip().upper()
                for od, count in (od_counts or {}).items():
                    current_global_od[od] = current_global_od.get(od, 0) + int(count or 0)
                    current_airlines_per_od.setdefault(od, set()).add(airline_code)
            for od_counts in next_counts_by_airline.values():
                for od, count in (od_counts or {}).items():
                    next_global_od[od] = next_global_od.get(od, 0) + int(count or 0)

            for airline, od_counts in current_counts_by_airline.items():
                airline_code = str(airline or "").strip().upper()
                homebases = set(get_homebases_for_airline(airline_code))
                for od, count in (od_counts or {}).items():
                    current_count = int(count or 0)
                    current_global = int(current_global_od.get(od) or 0)
                    competitors = len(current_airlines_per_od.get(od, set()) - {airline_code})
                    next_airline_count = int((next_counts_by_airline.get(airline_code) or {}).get(od, 0) or 0)
                    next_global = int(next_global_od.get(od) or 0)
                    current_share = round(current_count / current_global, 4) if current_global else 0.0
                    future_share = round(next_airline_count / next_global, 4) if next_global else 0.0
                    route_meta = route_lookup.get(od, {})
                    distance_km = int(route_meta.get("distance_km") or 0)
                    check24_features = get_latest_check24_features(
                        od,
                        current_dt,
                        check24_lookup,
                        max_age_hours=check24_window_hours,
                    )
                    aviationstack_features = get_latest_aviationstack_features(
                        od,
                        airline_code,
                        current_dt,
                        aviationstack_lookup,
                        max_age_hours=aux_window_hours,
                    )
                    airlabs_features = get_latest_airlabs_features(
                        od,
                        airline_code,
                        current_dt,
                        airlabs_lookup,
                        max_age_hours=aux_window_hours,
                    )
                    fr24_features = get_latest_fr24_features(
                        od,
                        airline_code,
                        current_dt,
                        fr24_lookup,
                        max_age_hours=aux_window_hours,
                    )
                    rows.append(
                        {
                            "snapshot_at": current_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "region": region,
                            "airline": airline_code,
                            "od": od,
                            "origin": od[:3],
                            "destination": od[4:7],
                            "distance_km": distance_km,
                            "demand_tier": str(route_meta.get("demand_tier") or ""),
                            "homebase_match": int(od[:3] in homebases or od[4:7] in homebases),
                            "current_airline_od_flights": current_count,
                            "current_global_od_flights": current_global,
                            "current_competitor_count": competitors,
                            "current_airline_od_share": current_share,
                            "future_airline_od_flights": next_airline_count,
                            "future_global_od_flights": next_global,
                            "future_airline_od_share": future_share,
                            "future_growth_ratio": round(next_airline_count / current_count, 4) if current_count else 0.0,
                            "future_share_delta": round(future_share - current_share, 4),
                            "label_increase_frequency": int(next_airline_count > current_count),
                            "label_share_gain": int(future_share > current_share),
                            "label_upgauge_pressure": int(next_airline_count >= current_count and current_global >= 8),
                            "horizon_hours": round((next_dt - current_dt).total_seconds() / 3600.0, 2),
                            "check24_yield_proxy_eur_per_1000km": compute_price_distance_proxy(
                                float(check24_features.get("check24_offer_avg_price_eur") or 0.0),
                                distance_km,
                            ),
                            "check24_direct_yield_proxy_eur_per_1000km": compute_price_distance_proxy(
                                float(check24_features.get("check24_direct_min_price_eur") or 0.0),
                                distance_km,
                            ),
                            **check24_features,
                            **aviationstack_features,
                            **airlabs_features,
                            **fr24_features,
                        }
                    )
    rows.sort(key=lambda item: (item["snapshot_at"], item["region"], item["airline"], item["od"]))
    return rows


def write_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a first supervised training dataset from historical raw flight snapshots.")
    parser.add_argument(
        "--output",
        default=str(PROCESSED_DIR / "training_dataset.csv"),
        help="Path to the output CSV file.",
    )
    parser.add_argument(
        "--aux-window-hours",
        type=float,
        default=24.0,
        help="Maximum distance in hours when matching Aviationstack and AirLabs snapshots to each OpenSky sample.",
    )
    parser.add_argument(
        "--check24-window-hours",
        type=float,
        default=336.0,
        help="Maximum distance in hours when matching Check24 web snapshots to each OpenSky sample.",
    )
    args = parser.parse_args()

    rows = build_rows(aux_window_hours=args.aux_window_hours, check24_window_hours=args.check24_window_hours)
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"wrote_rows={len(rows)}")
    print(f"output={output_path}")
    print(f"aux_window_hours={args.aux_window_hours}")
    print(f"check24_window_hours={args.check24_window_hours}")


if __name__ == "__main__":
    main()