import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
sys.path.insert(0, str(BASE_DIR))

from scripts.train_baseline_model import build_feature_matrix, build_priors, load_rows, predict, ridge_fit, time_split, to_float
from src.decision_policy import DecisionInputs, recommend_action


ACTION_PRIORITY = {
    "launch route": 0,
    "upgauge": 1,
    "add frequency": 2,
    "hold": 3,
    "reduce / defend selectively": 4,
}

SUPPORT_PRIORITY = {
    "high": 3,
    "medium": 2,
    "baseline": 1,
    "sparse": 0,
}


def infer_support(row: Dict[str, Any]) -> tuple[str, List[str]]:
    sources: List[str] = []
    if to_float(row, "current_global_od_flights") > 0:
        sources.append("opensky-history")
    if to_float(row, "airlabs_route_records") > 0:
        sources.append("airlabs")
    if to_float(row, "aviationstack_route_records") > 0:
        sources.append("aviationstack")
    if to_float(row, "check24_records") > 0:
        sources.append("check24-web")

    auxiliary_count = sum(1 for source in sources if source != "opensky-history")
    if auxiliary_count >= 2:
        level = "high"
    elif auxiliary_count == 1:
        level = "medium"
    elif sources:
        level = "baseline"
    else:
        level = "sparse"
    return level, sources


def build_recommendations(dataset_path: Path, alpha: float, test_ratio: float, limit: int) -> List[Dict[str, Any]]:
    rows = load_rows(dataset_path)
    train_rows, test_rows = time_split(rows, test_ratio=test_ratio)
    priors = build_priors(train_rows)
    train_x, _ = build_feature_matrix(train_rows, priors)
    score_x, _ = build_feature_matrix(rows, priors)

    train_y_flights = [to_float(row, "future_airline_od_flights") for row in train_rows]
    train_y_share = [to_float(row, "future_airline_od_share") for row in train_rows]

    flights_weights = ridge_fit(train_x, _to_array(train_y_flights), alpha=alpha)
    share_weights = ridge_fit(train_x, _to_array(train_y_share), alpha=alpha)

    pred_flights = predict(score_x, flights_weights)
    pred_share = score_x @ share_weights

    recommendations: List[Dict[str, Any]] = []
    test_identity = {id(row) for row in test_rows}
    for row, future_flights, future_share in zip(rows, pred_flights, pred_share):
        current_share = to_float(row, "current_airline_od_share")
        support_level, support_sources = infer_support(row)
        recommendation = recommend_action(
            DecisionInputs(
                airline=row.get("airline", ""),
                od=row.get("od", ""),
                current_airline_od_flights=to_float(row, "current_airline_od_flights"),
                current_airline_od_share=current_share,
                current_global_od_flights=to_float(row, "current_global_od_flights"),
                current_competitor_count=to_float(row, "current_competitor_count"),
                homebase_match=to_float(row, "homebase_match"),
                predicted_future_airline_od_flights=float(future_flights),
                predicted_future_airline_od_share=float(max(min(future_share, 1.0), 0.0)),
                predicted_share_delta=float(max(min(future_share, 1.0), 0.0) - current_share),
                current_route_avg_seats=to_float(row, "airlabs_route_avg_seats"),
                current_target_airline_avg_seats=to_float(row, "airlabs_target_airline_avg_seats"),
                current_yield_proxy_eur_per_1000km=to_float(row, "check24_yield_proxy_eur_per_1000km"),
            )
        )
        recommendations.append(
            {
                "snapshot_at": row.get("snapshot_at", ""),
                "airline": row.get("airline", ""),
                "od": row.get("od", ""),
                "current_airline_od_flights": to_float(row, "current_airline_od_flights"),
                "current_airline_od_share": current_share,
                "predicted_future_airline_od_flights": round(float(future_flights), 4),
                "predicted_future_airline_od_share": round(float(max(min(future_share, 1.0), 0.0)), 4),
                "predicted_share_delta": round(float(max(min(future_share, 1.0), 0.0) - current_share), 4),
                "current_route_avg_seats": to_float(row, "airlabs_route_avg_seats"),
                "current_target_airline_avg_seats": to_float(row, "airlabs_target_airline_avg_seats"),
                "current_yield_proxy_eur_per_1000km": to_float(row, "check24_yield_proxy_eur_per_1000km"),
                "scoring_split": "test" if id(row) in test_identity else "train",
                "support_level": support_level,
                "support_sources": support_sources,
                "action": recommendation.action,
                "confidence": recommendation.confidence,
                "rationale": recommendation.rationale,
            }
        )

    recommendations.sort(
        key=lambda item: (
            ACTION_PRIORITY.get(str(item.get("action") or ""), 99),
            -SUPPORT_PRIORITY.get(str(item.get("support_level") or "").lower(), -1),
            -float(item.get("confidence") or 0.0),
            -float(item.get("predicted_future_airline_od_flights") or 0.0),
        )
    )
    if limit and limit > 0:
        return recommendations[:limit]
    return recommendations


def _to_array(values: List[float]):
    import numpy as np

    return np.array(values, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate transparent route-action recommendations from the baseline demand/share models.")
    parser.add_argument(
        "--dataset",
        default=str(PROCESSED_DIR / "training_dataset.csv"),
        help="Path to the training dataset CSV.",
    )
    parser.add_argument(
        "--output",
        default=str(PROCESSED_DIR / "decision_policy_recommendations.json"),
        help="Path to the output JSON file.",
    )
    parser.add_argument("--alpha", type=float, default=1.0, help="Ridge regularization strength.")
    parser.add_argument("--test-ratio", type=float, default=0.2, help="Chronological holdout ratio.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum recommendations to output. Use 0 for all rows.")
    args = parser.parse_args()

    recommendations = build_recommendations(Path(args.dataset), alpha=args.alpha, test_ratio=args.test_ratio, limit=args.limit)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(recommendations, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote_recommendations={len(recommendations)}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()