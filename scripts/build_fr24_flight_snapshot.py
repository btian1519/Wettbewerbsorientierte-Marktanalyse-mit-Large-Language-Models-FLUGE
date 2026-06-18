import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "fr24"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

OUTPUT_FIELDS = [
    "snapshot_at",
    "airline_iata",
    "origin",
    "destination",
    "aircraft_icao",
    "seat_capacity",
    "flight_number",
    "source_file",
]


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing timestamp")
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_raw_rows() -> List[Dict[str, Any]]:
    if not RAW_DIR.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for path in sorted(RAW_DIR.glob("*")):
        if path.suffix.lower() == ".csv":
            rows.extend(_read_csv_rows(path))
        elif path.suffix.lower() == ".json":
            rows.extend(_read_json_rows(path))
    return rows


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row, _source_file=path.name) for row in csv.DictReader(handle)]
    except Exception:
        return []


def _read_json_rows(path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(payload, list):
        return [dict(item, _source_file=path.name) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            return [dict(item, _source_file=path.name) for item in payload.get("data") if isinstance(item, dict)]
        return [dict(payload, _source_file=path.name)]
    return []


def _lower_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def _first_non_empty(row: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _parse_seat_capacity(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _infer_airline_iata(flight_number: str) -> str:
    text = str(flight_number or "").strip().upper()
    letters = "".join(char for char in text if char.isalpha())
    return letters[:2] if len(letters) >= 2 else ""


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any] | None:
    lower = _lower_keys(row)
    snapshot_text = _first_non_empty(
        lower,
        ["snapshot_at", "collected_at", "observed_at", "date", "flight_date", "day"],
    )
    if not snapshot_text:
        return None
    try:
        snapshot_dt = parse_timestamp(snapshot_text)
    except Exception:
        return None

    origin = _first_non_empty(lower, ["origin", "origin_iata", "dep_iata", "from", "departure_iata"]).upper()
    destination = _first_non_empty(lower, ["destination", "destination_iata", "arr_iata", "to", "arrival_iata"]).upper()
    if len(origin) != 3 or len(destination) != 3:
        return None

    flight_number = _first_non_empty(lower, ["flight_number", "flight", "callsign", "number"]).upper()
    airline_iata = _first_non_empty(lower, ["airline_iata", "carrier_iata", "operator_iata", "airline", "carrier"]).upper()
    if not airline_iata and flight_number:
        airline_iata = _infer_airline_iata(flight_number)
    aircraft_icao = _first_non_empty(lower, ["aircraft_icao", "aircraft_type", "aircraft", "equipment"]).upper()
    seat_capacity = _parse_seat_capacity(_first_non_empty(lower, ["seat_capacity", "seats", "aircraft_seats"]))

    return {
        "snapshot_at": snapshot_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "airline_iata": airline_iata,
        "origin": origin,
        "destination": destination,
        "aircraft_icao": aircraft_icao,
        "seat_capacity": round(seat_capacity, 2) if seat_capacity > 0 else "",
        "flight_number": flight_number,
        "source_file": str(row.get("_source_file") or ""),
    }


def build_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw_row in read_raw_rows():
        normalized = normalize_row(raw_row)
        if normalized is not None:
            rows.append(normalized)
    rows.sort(
        key=lambda item: (
            item["snapshot_at"],
            item["airline_iata"],
            item["origin"],
            item["destination"],
            item["flight_number"],
        )
    )
    return rows


def write_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a normalized FR24 flight snapshot CSV from raw CSV or JSON exports in data/raw/fr24/."
    )
    parser.add_argument(
        "--output",
        default=str(PROCESSED_DIR / "fr24_flight_snapshot.csv"),
        help="Path to the normalized FR24 snapshot CSV.",
    )
    args = parser.parse_args()

    rows = build_rows()
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"wrote_rows={len(rows)}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()