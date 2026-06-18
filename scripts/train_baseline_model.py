import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
sys.path.insert(0, str(BASE_DIR))


NUMERIC_COLUMNS = [
    "current_airline_od_flights",
    "current_global_od_flights",
    "current_competitor_count",
    "current_airline_od_share",
    "homebase_match",
    "horizon_hours",
    "distance_km",
    "check24_records",
    "check24_direct_count",
    "check24_direct_min_price_eur",
    "check24_offer_min_price_eur",
    "check24_offer_avg_price_eur",
    "check24_direct_offer_share",
]


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def time_split(rows: Sequence[Dict[str, str]], test_ratio: float) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    snapshots = sorted({row["snapshot_at"] for row in rows})
    if len(snapshots) < 2:
        raise ValueError("Need at least two distinct snapshot timestamps for a chronological split.")

    test_count = max(1, int(math.ceil(len(snapshots) * test_ratio)))
    if test_count >= len(snapshots):
        test_count = len(snapshots) - 1
    train_snapshots = set(snapshots[:-test_count])
    test_snapshots = set(snapshots[-test_count:])
    train_rows = [row for row in rows if row["snapshot_at"] in train_snapshots]
    test_rows = [row for row in rows if row["snapshot_at"] in test_snapshots]
    return train_rows, test_rows


def to_float(row: Dict[str, str], key: str) -> float:
    value = str(row.get(key, "") or "").strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def build_priors(train_rows: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    airline_target_sum: Dict[str, float] = defaultdict(float)
    airline_target_count: Dict[str, int] = defaultdict(int)
    od_target_sum: Dict[str, float] = defaultdict(float)
    od_target_count: Dict[str, int] = defaultdict(int)
    global_target_sum = 0.0

    for row in train_rows:
        target = to_float(row, "future_airline_od_flights")
        airline = row.get("airline", "")
        od = row.get("od", "")
        airline_target_sum[airline] += target
        airline_target_count[airline] += 1
        od_target_sum[od] += target
        od_target_count[od] += 1
        global_target_sum += target

    global_mean = global_target_sum / len(train_rows) if train_rows else 0.0
    airline_mean = {
        airline: airline_target_sum[airline] / airline_target_count[airline]
        for airline in airline_target_sum
    }
    od_mean = {od: od_target_sum[od] / od_target_count[od] for od in od_target_sum}
    return {
        "global": {"future_airline_od_flights_mean": global_mean},
        "airline": airline_mean,
        "od": od_mean,
    }


def build_feature_matrix(rows: Sequence[Dict[str, str]], priors: Dict[str, Dict[str, float]]) -> Tuple[np.ndarray, List[str]]:
    feature_names = [
        "bias",
        "log_current_airline_od_flights",
        "log_current_global_od_flights",
        "current_competitor_count",
        "current_airline_od_share",
        "homebase_match",
        "horizon_hours",
        "distance_km",
        "check24_records",
        "check24_direct_count",
        "check24_direct_min_price_eur",
        "check24_offer_min_price_eur",
        "check24_offer_avg_price_eur",
        "check24_direct_offer_share",
        "check24_offer_lead_time_days",
        "check24_snapshot_age_hours",
        "check24_yield_proxy_eur_per_1000km",
        "check24_direct_yield_proxy_eur_per_1000km",
        "aviationstack_route_records",
        "aviationstack_route_airline_count",
        "aviationstack_target_airline_records",
        "aviationstack_target_airline_present",
        "aviationstack_route_departure_hour_avg",
        "aviationstack_route_scheduled_share",
        "airlabs_route_records",
        "airlabs_route_airline_count",
        "airlabs_target_airline_records",
        "airlabs_target_airline_present",
        "airlabs_route_avg_speed",
        "airlabs_route_aircraft_type_count",
        "airlabs_route_avg_seats",
        "airlabs_route_total_capacity_proxy",
        "airlabs_target_airline_avg_seats",
        "fr24_route_records",
        "fr24_route_airline_count",
        "fr24_target_airline_records",
        "fr24_target_airline_present",
        "fr24_route_aircraft_type_count",
        "fr24_route_avg_seats",
        "fr24_route_total_capacity_proxy",
        "fr24_target_airline_avg_seats",
        "airline_target_prior",
        "od_target_prior",
        "global_target_prior",
    ]
    matrix = np.zeros((len(rows), len(feature_names)), dtype=float)
    global_prior = float(priors["global"]["future_airline_od_flights_mean"])
    for row_index, row in enumerate(rows):
        current_airline = to_float(row, "current_airline_od_flights")
        current_global = to_float(row, "current_global_od_flights")
        airline = row.get("airline", "")
        od = row.get("od", "")
        matrix[row_index] = [
            1.0,
            math.log1p(current_airline),
            math.log1p(current_global),
            to_float(row, "current_competitor_count"),
            to_float(row, "current_airline_od_share"),
            to_float(row, "homebase_match"),
            to_float(row, "horizon_hours"),
            to_float(row, "distance_km"),
            to_float(row, "check24_records"),
            to_float(row, "check24_direct_count"),
            to_float(row, "check24_direct_min_price_eur"),
            to_float(row, "check24_offer_min_price_eur"),
            to_float(row, "check24_offer_avg_price_eur"),
            to_float(row, "check24_direct_offer_share"),
            to_float(row, "check24_offer_lead_time_days"),
            to_float(row, "check24_snapshot_age_hours"),
            to_float(row, "check24_yield_proxy_eur_per_1000km"),
            to_float(row, "check24_direct_yield_proxy_eur_per_1000km"),
            to_float(row, "aviationstack_route_records"),
            to_float(row, "aviationstack_route_airline_count"),
            to_float(row, "aviationstack_target_airline_records"),
            to_float(row, "aviationstack_target_airline_present"),
            to_float(row, "aviationstack_route_departure_hour_avg"),
            to_float(row, "aviationstack_route_scheduled_share"),
            to_float(row, "airlabs_route_records"),
            to_float(row, "airlabs_route_airline_count"),
            to_float(row, "airlabs_target_airline_records"),
            to_float(row, "airlabs_target_airline_present"),
            to_float(row, "airlabs_route_avg_speed"),
            to_float(row, "airlabs_route_aircraft_type_count"),
            to_float(row, "airlabs_route_avg_seats"),
            to_float(row, "airlabs_route_total_capacity_proxy"),
            to_float(row, "airlabs_target_airline_avg_seats"),
            to_float(row, "fr24_route_records"),
            to_float(row, "fr24_route_airline_count"),
            to_float(row, "fr24_target_airline_records"),
            to_float(row, "fr24_target_airline_present"),
            to_float(row, "fr24_route_aircraft_type_count"),
            to_float(row, "fr24_route_avg_seats"),
            to_float(row, "fr24_route_total_capacity_proxy"),
            to_float(row, "fr24_target_airline_avg_seats"),
            float(priors["airline"].get(airline, global_prior)),
            float(priors["od"].get(od, global_prior)),
            global_prior,
        ]
    return matrix, feature_names


def ridge_fit(features: np.ndarray, target: np.ndarray, alpha: float) -> np.ndarray:
    reg = np.eye(features.shape[1], dtype=float)
    reg[0, 0] = 0.0
    lhs = features.T @ features + alpha * reg
    rhs = features.T @ target
    return np.linalg.solve(lhs, rhs)


def predict(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.maximum(features @ weights, 0.0)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y_true - y_pred))))


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.square(y_true - np.mean(y_true))))
    if denom == 0.0:
        return 0.0
    return float(1.0 - (np.sum(np.square(y_true - y_pred)) / denom))


def classification_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    y_pred = (y_score >= threshold).astype(int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    accuracy = (tp + tn) / len(y_true) if len(y_true) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    balanced_accuracy = (recall + specificity) / 2.0
    return {
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "balanced_accuracy": round(float(balanced_accuracy), 4),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def evaluate(train_rows: Sequence[Dict[str, str]], test_rows: Sequence[Dict[str, str]], alpha: float) -> Dict[str, object]:
    priors = build_priors(train_rows)
    train_x, feature_names = build_feature_matrix(train_rows, priors)
    test_x, _ = build_feature_matrix(test_rows, priors)

    train_y_reg = np.array([to_float(row, "future_airline_od_flights") for row in train_rows], dtype=float)
    test_y_reg = np.array([to_float(row, "future_airline_od_flights") for row in test_rows], dtype=float)
    train_y_share = np.array([to_float(row, "future_airline_od_share") for row in train_rows], dtype=float)
    test_y_share = np.array([to_float(row, "future_airline_od_share") for row in test_rows], dtype=float)
    train_y_cls = np.array([to_float(row, "label_increase_frequency") for row in train_rows], dtype=float)
    test_y_cls = np.array([to_float(row, "label_increase_frequency") for row in test_rows], dtype=float)
    train_y_share_cls = np.array([to_float(row, "label_share_gain") for row in train_rows], dtype=float)
    test_y_share_cls = np.array([to_float(row, "label_share_gain") for row in test_rows], dtype=float)

    reg_weights = ridge_fit(train_x, train_y_reg, alpha=alpha)
    reg_pred = predict(test_x, reg_weights)
    naive_reg_pred = np.array([to_float(row, "current_airline_od_flights") for row in test_rows], dtype=float)

    share_weights = ridge_fit(train_x, train_y_share, alpha=alpha)
    share_pred = np.clip(test_x @ share_weights, 0.0, 1.0)
    naive_share_pred = np.array([to_float(row, "current_airline_od_share") for row in test_rows], dtype=float)

    cls_weights = ridge_fit(train_x, train_y_cls, alpha=alpha)
    cls_score = np.clip(test_x @ cls_weights, 0.0, 1.0)
    naive_cls_score = np.zeros_like(test_y_cls)

    share_cls_weights = ridge_fit(train_x, train_y_share_cls, alpha=alpha)
    share_cls_score = np.clip(test_x @ share_cls_weights, 0.0, 1.0)
    naive_share_cls_score = np.zeros_like(test_y_share_cls)

    return {
        "split": {
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "train_snapshots": len({row["snapshot_at"] for row in train_rows}),
            "test_snapshots": len({row["snapshot_at"] for row in test_rows}),
            "test_ratio": round(len({row['snapshot_at'] for row in test_rows}) / len({row['snapshot_at'] for row in train_rows + test_rows}), 4),
        },
        "regression": {
            "target": "future_airline_od_flights",
            "mae": round(mae(test_y_reg, reg_pred), 4),
            "rmse": round(rmse(test_y_reg, reg_pred), 4),
            "r2": round(r2(test_y_reg, reg_pred), 4),
            "naive_mae": round(mae(test_y_reg, naive_reg_pred), 4),
            "naive_rmse": round(rmse(test_y_reg, naive_reg_pred), 4),
        },
        "share_regression": {
            "target": "future_airline_od_share",
            "mae": round(mae(test_y_share, share_pred), 4),
            "rmse": round(rmse(test_y_share, share_pred), 4),
            "r2": round(r2(test_y_share, share_pred), 4),
            "naive_mae": round(mae(test_y_share, naive_share_pred), 4),
            "naive_rmse": round(rmse(test_y_share, naive_share_pred), 4),
        },
        "classification": {
            "target": "label_increase_frequency",
            "model": classification_metrics(test_y_cls, cls_score),
            "naive_all_zero": classification_metrics(test_y_cls, naive_cls_score),
        },
        "share_classification": {
            "target": "label_share_gain",
            "model": classification_metrics(test_y_share_cls, share_cls_score),
            "naive_all_zero": classification_metrics(test_y_share_cls, naive_share_cls_score),
        },
        "feature_names": feature_names,
        "regression_weights": {name: round(float(weight), 6) for name, weight in zip(feature_names, reg_weights)},
        "share_regression_weights": {name: round(float(weight), 6) for name, weight in zip(feature_names, share_weights)},
        "classification_weights": {name: round(float(weight), 6) for name, weight in zip(feature_names, cls_weights)},
        "share_classification_weights": {name: round(float(weight), 6) for name, weight in zip(feature_names, share_cls_weights)},
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a first chronological baseline model on the generated airline-route dataset.")
    parser.add_argument(
        "--dataset",
        default=str(PROCESSED_DIR / "training_dataset.csv"),
        help="Path to the training dataset CSV generated by build_training_dataset.py.",
    )
    parser.add_argument(
        "--report",
        default=str(PROCESSED_DIR / "baseline_model_report.json"),
        help="Path to the output metrics/weights JSON report.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge regularization strength.",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="Chronological holdout ratio based on unique snapshot timestamps.",
    )
    args = parser.parse_args()

    rows = load_rows(Path(args.dataset))
    train_rows, test_rows = time_split(rows, test_ratio=args.test_ratio)
    report = evaluate(train_rows, test_rows, alpha=args.alpha)
    write_json(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()