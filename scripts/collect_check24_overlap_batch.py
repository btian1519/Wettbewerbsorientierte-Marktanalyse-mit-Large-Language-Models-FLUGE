import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
sys.path.insert(0, str(BASE_DIR))

from src.collect_sources import CollectConfig, collect_once


def load_training_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_ranked_od_list(rows: List[Dict[str, Any]], limit: int, min_global_flights: float) -> List[Dict[str, Any]]:
    aggregates: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"current_global_od_flights": 0.0, "row_count": 0, "last_snapshot_at": ""})
    for row in rows:
        od = str(row.get("od") or "").strip().upper()
        if not od or "-" not in od:
            continue
        origin, destination = [token.strip().upper() for token in od.split("-", 1)]
        if len(origin) != 3 or len(destination) != 3:
            continue

        current_global = to_float(row.get("current_global_od_flights"))
        if current_global < min_global_flights:
            continue

        bucket = aggregates[od]
        bucket["od"] = od
        bucket["origin"] = origin
        bucket["destination"] = destination
        bucket["current_global_od_flights"] = max(bucket["current_global_od_flights"], current_global)
        bucket["row_count"] += 1
        snapshot_at = str(row.get("snapshot_at") or "")
        if snapshot_at > str(bucket["last_snapshot_at"] or ""):
            bucket["last_snapshot_at"] = snapshot_at

    ranked = sorted(
        aggregates.values(),
        key=lambda item: (-float(item.get("current_global_od_flights") or 0.0), -int(item.get("row_count") or 0), str(item.get("od") or "")),
    )
    return ranked[:limit]


def to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def default_return_date(departure_date: str, trip_days: int) -> str:
    return (date.fromisoformat(departure_date) + timedelta(days=trip_days)).isoformat()


def collect_ranked_ods(
    candidates: List[Dict[str, Any]],
    departure_date: str,
    return_date: str,
    adults: int,
    max_offers: int,
    dry_run: bool,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for candidate in candidates:
        if dry_run:
            results.append(
                {
                    "od": candidate.get("od"),
                    "origin": candidate.get("origin"),
                    "destination": candidate.get("destination"),
                    "current_global_od_flights": candidate.get("current_global_od_flights"),
                    "row_count": candidate.get("row_count"),
                    "status": "planned",
                    "records": 0,
                    "path": "",
                    "error": "",
                }
            )
            continue
        cfg = CollectConfig(
            origin=str(candidate.get("origin") or ""),
            destination=str(candidate.get("destination") or ""),
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            dep_iata=str(candidate.get("origin") or ""),
            arr_iata=str(candidate.get("destination") or ""),
            use_opensky=False,
            use_eurostat=False,
            use_amadeus=False,
            use_aviationstack=False,
            use_airlabs=False,
            use_check24=True,
            check24_max_offers=max_offers,
        )
        outcome = collect_once(cfg)
        success = next((item for item in outcome.get("ok") or [] if item.get("source") == "check24"), None)
        warning = next((item for item in outcome.get("warn") or [] if item.get("source") == "check24"), None)
        results.append(
            {
                "od": candidate.get("od"),
                "origin": candidate.get("origin"),
                "destination": candidate.get("destination"),
                "current_global_od_flights": candidate.get("current_global_od_flights"),
                "row_count": candidate.get("row_count"),
                "status": "ok" if success else "warn",
                "records": int(success.get("records") or 0) if success else 0,
                "path": str(success.get("path") or "") if success else "",
                "error": str(warning.get("error") or "") if warning else "",
            }
        )
    return {
        "departure_date": departure_date,
        "return_date": return_date,
        "adults": adults,
        "max_offers": max_offers,
        "requested_ods": len(candidates),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Check24 payloads for high-coverage ODs already present in the training dataset.")
    parser.add_argument("--dataset", default=str(PROCESSED_DIR / "training_dataset.csv"), help="Training dataset CSV used to rank overlapping ODs.")
    parser.add_argument("--output", default=str(PROCESSED_DIR / "check24_overlap_batch_report.json"), help="Batch report JSON path.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of ODs to collect.")
    parser.add_argument("--min-global-flights", type=float, default=20.0, help="Minimum observed global OD flights required for selection.")
    parser.add_argument("--departure-date", default=(date.today() + timedelta(days=21)).isoformat(), help="Departure date for Check24 collection.")
    parser.add_argument("--trip-days", type=int, default=7, help="Return offset in days if --return-date is not set.")
    parser.add_argument("--return-date", default="", help="Return date for Check24 collection.")
    parser.add_argument("--adults", type=int, default=1, help="Number of adults for Check24 collection.")
    parser.add_argument("--max-offers", type=int, default=5, help="Maximum Check24 offers to capture per OD.")
    parser.add_argument("--dry-run", action="store_true", help="Only rank and report overlapping ODs without opening Check24.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    rows = load_training_rows(dataset_path)
    candidates = build_ranked_od_list(rows, limit=args.limit, min_global_flights=args.min_global_flights)
    return_date = args.return_date or default_return_date(args.departure_date, args.trip_days)

    report = collect_ranked_ods(
        candidates=candidates,
        departure_date=args.departure_date,
        return_date=return_date,
        adults=args.adults,
        max_offers=args.max_offers,
        dry_run=args.dry_run,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"selected_ods={len(candidates)}")
    for item in candidates:
        print(f"candidate={item['od']} global_flights={int(item['current_global_od_flights'])} rows={item['row_count']}")
    print(f"output={output_path}")
    ok_count = sum(1 for item in report["results"] if item.get("status") == "ok")
    planned_count = sum(1 for item in report["results"] if item.get("status") == "planned")
    if args.dry_run:
        print(f"planned_ods={planned_count}")
    else:
        print(f"check24_ok={ok_count}")


if __name__ == "__main__":
    main()