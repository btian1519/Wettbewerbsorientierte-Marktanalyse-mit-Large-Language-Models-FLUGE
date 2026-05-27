import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "check24"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def parse_collected_at(value: Any) -> datetime:
    text = str(value or "").strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value!r}")


def load_raw_payloads() -> List[Dict[str, Any]]:
    if not RAW_DIR.exists():
        return []

    payloads: List[Dict[str, Any]] = []
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_file_path"] = str(path)
            payloads.append(payload)
        except Exception:
            continue
    return payloads


def build_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for payload in load_raw_payloads():
        try:
            collected_dt = parse_collected_at(payload.get("collected_at"))
        except Exception:
            continue

        query = payload.get("query") or {}
        origin = str(query.get("origin") or "").strip().upper()
        destination = str(query.get("destination") or "").strip().upper()
        departure_date = str(query.get("departure_date") or "").strip()
        return_date = str(query.get("return_date") or "").strip()
        od = f"{origin}-{destination}" if origin and destination else ""
        lead_time_days = compute_lead_time_days(collected_dt, departure_date)
        summary = payload.get("summary") or {}

        for offer_index, offer in enumerate(payload.get("offers") or []):
            flights = offer.get("flights") or []
            carriers = [str(value).strip() for value in (offer.get("carriers") or []) if str(value).strip()]
            stops = [str(value).strip() for value in (offer.get("stops") or []) if str(value).strip()]
            outbound = flights[0] if len(flights) >= 1 and isinstance(flights[0], dict) else {}
            inbound = flights[1] if len(flights) >= 2 and isinstance(flights[1], dict) else {}
            rows.append(
                {
                    "snapshot_at": collected_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "od": od,
                    "origin": origin,
                    "destination": destination,
                    "outbound_travel_date": departure_date,
                    "return_travel_date": return_date,
                    "lead_time_days": lead_time_days,
                    "offer_index": offer_index,
                    "offer_label": str(offer.get("label") or ""),
                    "price_eur": float(offer.get("price_eur") or 0.0),
                    "price_text": str(offer.get("price_text") or ""),
                    "carrier_count": len(carriers),
                    "carriers": " | ".join(carriers),
                    "outbound_carrier": str(offer.get("outbound_carrier") or ""),
                    "inbound_carrier": str(offer.get("inbound_carrier") or ""),
                    "is_direct": int(any(value.lower() == "direkt" for value in stops)),
                    "stops_summary": " | ".join(stops),
                    "luggage": str(offer.get("luggage") or ""),
                    "dynamic_points": str(offer.get("dynamic_points") or ""),
                    "outbound_departure_time": str(outbound.get("departure_time") or ""),
                    "outbound_arrival_time": str(outbound.get("arrival_time") or ""),
                    "outbound_duration_text": str(outbound.get("duration") or ""),
                    "inbound_departure_time": str(inbound.get("departure_time") or ""),
                    "inbound_arrival_time": str(inbound.get("arrival_time") or ""),
                    "inbound_duration_text": str(inbound.get("duration") or ""),
                    "summary_headline": str(summary.get("headline") or ""),
                    "summary_direct_count": parse_int(summary.get("direct_count")),
                    "summary_direct_min_price_eur": parse_eur(summary.get("direct_min_price")),
                }
            )
    rows.sort(key=lambda item: (item["snapshot_at"], item["od"], item["outbound_travel_date"], item["offer_index"]))
    return rows


def compute_lead_time_days(collected_dt: datetime, departure_date: str) -> int:
    try:
        departure_dt = datetime.fromisoformat(departure_date).replace(tzinfo=timezone.utc)
    except ValueError:
        return 0
    return int((departure_dt.date() - collected_dt.date()).days)


def parse_int(value: Any) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


def parse_eur(value: Any) -> float:
    text = str(value or "").replace("Ab", "").replace("€", "").replace("\xa0", " ").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def write_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a normalized Check24 offer snapshot table from raw browser-collected payloads.")
    parser.add_argument(
        "--output",
        default=str(PROCESSED_DIR / "check24_offer_snapshot.csv"),
        help="Path to the normalized Check24 offer snapshot CSV.",
    )
    args = parser.parse_args()

    rows = build_rows()
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"wrote_rows={len(rows)}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()