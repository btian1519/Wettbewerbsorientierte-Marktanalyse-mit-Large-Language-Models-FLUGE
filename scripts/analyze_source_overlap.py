import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


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


def extract_opensky_sets() -> Tuple[Set[str], Set[Tuple[str, str]], List[str]]:
    od_set: Set[str] = set()
    pair_set: Set[Tuple[str, str]] = set()
    collected_at: List[str] = []
    for payload in load_json_files("opensky_flights"):
        collected_at.append(str(payload.get("collected_at") or ""))
        for airline, od_counts in (payload.get("od_counts") or {}).items():
            airline_code = str(airline or "").strip().upper()
            for od in (od_counts or {}).keys():
                od_text = str(od or "").strip().upper()
                if not _is_valid_od(od_text):
                    continue
                od_set.add(od_text)
                if airline_code:
                    pair_set.add((airline_code, od_text))
    return od_set, pair_set, sorted(value for value in collected_at if value)


def extract_aviationstack_sets() -> Tuple[Set[str], Set[Tuple[str, str]], List[str]]:
    od_set: Set[str] = set()
    pair_set: Set[Tuple[str, str]] = set()
    collected_at: List[str] = []
    for payload in load_json_files("aviationstack"):
        collected_at.append(str(payload.get("collected_at") or ""))
        for record in ((payload.get("data") or {}).get("data") or []):
            if not isinstance(record, dict):
                continue
            departure = record.get("departure") or {}
            arrival = record.get("arrival") or {}
            airline = record.get("airline") or {}
            dep_iata = str(departure.get("iata") or "").strip().upper()
            arr_iata = str(arrival.get("iata") or "").strip().upper()
            airline_code = str(airline.get("iata") or "").strip().upper()
            od = f"{dep_iata}-{arr_iata}"
            if not _is_valid_od(od):
                continue
            od_set.add(od)
            if airline_code:
                pair_set.add((airline_code, od))
    return od_set, pair_set, sorted(value for value in collected_at if value)


def extract_airlabs_sets() -> Tuple[Set[str], Set[Tuple[str, str]], List[str]]:
    od_set: Set[str] = set()
    pair_set: Set[Tuple[str, str]] = set()
    collected_at: List[str] = []
    for payload in load_json_files("airlabs"):
        collected_at.append(str(payload.get("collected_at") or ""))
        for record in ((payload.get("data") or {}).get("response") or []):
            if not isinstance(record, dict):
                continue
            dep_iata = str(record.get("dep_iata") or "").strip().upper()
            arr_iata = str(record.get("arr_iata") or "").strip().upper()
            airline_code = str(record.get("airline_iata") or "").strip().upper()
            od = f"{dep_iata}-{arr_iata}"
            if not _is_valid_od(od):
                continue
            od_set.add(od)
            if airline_code:
                pair_set.add((airline_code, od))
    return od_set, pair_set, sorted(value for value in collected_at if value)


def _is_valid_od(od: str) -> bool:
    return len(od) == 7 and od[3] == "-" and od[:3].isalpha() and od[4:7].isalpha()


def summarize_overlap(base_od: Set[str], base_pairs: Set[Tuple[str, str]], compare_od: Set[str], compare_pairs: Set[Tuple[str, str]]) -> Dict[str, Any]:
    od_overlap = base_od & compare_od
    pair_overlap = base_pairs & compare_pairs
    return {
        "base_od_count": len(base_od),
        "compare_od_count": len(compare_od),
        "od_overlap_count": len(od_overlap),
        "od_overlap_ratio_vs_base": round(len(od_overlap) / len(base_od), 4) if base_od else 0.0,
        "base_pair_count": len(base_pairs),
        "compare_pair_count": len(compare_pairs),
        "pair_overlap_count": len(pair_overlap),
        "pair_overlap_ratio_vs_base": round(len(pair_overlap) / len(base_pairs), 4) if base_pairs else 0.0,
        "sample_overlap_od": sorted(list(od_overlap))[:25],
        "sample_overlap_pairs": [f"{airline}:{od}" for airline, od in sorted(list(pair_overlap))[:25]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze OD and airline-route overlap between OpenSky training snapshots and auxiliary data sources.")
    parser.add_argument(
        "--output",
        default=str(PROCESSED_DIR / "source_overlap_report.json"),
        help="Path to the JSON report.",
    )
    args = parser.parse_args()

    opensky_od, opensky_pairs, opensky_times = extract_opensky_sets()
    aviationstack_od, aviationstack_pairs, aviationstack_times = extract_aviationstack_sets()
    airlabs_od, airlabs_pairs, airlabs_times = extract_airlabs_sets()

    report = {
        "opensky_flights": {
            "snapshot_count": len(opensky_times),
            "snapshots": opensky_times,
            "od_count": len(opensky_od),
            "airline_od_count": len(opensky_pairs),
        },
        "aviationstack_vs_opensky": {
            "snapshot_count": len(aviationstack_times),
            "snapshots": aviationstack_times,
            **summarize_overlap(opensky_od, opensky_pairs, aviationstack_od, aviationstack_pairs),
        },
        "airlabs_vs_opensky": {
            "snapshot_count": len(airlabs_times),
            "snapshots": airlabs_times,
            **summarize_overlap(opensky_od, opensky_pairs, airlabs_od, airlabs_pairs),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()