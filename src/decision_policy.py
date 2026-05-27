from dataclasses import dataclass
from typing import List


@dataclass
class DecisionInputs:
    airline: str
    od: str
    current_airline_od_flights: float
    current_airline_od_share: float
    current_global_od_flights: float
    current_competitor_count: float
    homebase_match: float
    predicted_future_airline_od_flights: float
    predicted_future_airline_od_share: float
    predicted_share_delta: float
    current_route_avg_seats: float = 0.0
    current_target_airline_avg_seats: float = 0.0
    current_yield_proxy_eur_per_1000km: float = 0.0


@dataclass
class DecisionRecommendation:
    action: str
    confidence: float
    rationale: List[str]


def recommend_action(inputs: DecisionInputs) -> DecisionRecommendation:
    rationale: List[str] = []
    demand_growth = inputs.predicted_future_airline_od_flights - inputs.current_airline_od_flights
    demand_growth_ratio = (
        demand_growth / inputs.current_airline_od_flights if inputs.current_airline_od_flights > 0 else 0.0
    )
    share_gain = inputs.predicted_share_delta
    yield_proxy = inputs.current_yield_proxy_eur_per_1000km

    if inputs.current_airline_od_flights <= 0:
        if inputs.predicted_future_airline_od_flights >= 2.0 and inputs.homebase_match >= 1 and inputs.current_competitor_count <= 2:
            rationale.append("No current operation on this OD, but predicted demand is non-trivial.")
            rationale.append("Homebase fit is positive and competitor pressure is limited.")
            return DecisionRecommendation("launch route", _confidence(0.78, share_gain, demand_growth_ratio), rationale)
        rationale.append("No current operation and predicted demand signal is still weak.")
        return DecisionRecommendation("hold", _confidence(0.52, share_gain, demand_growth_ratio), rationale)

    seat_proxy = inputs.current_target_airline_avg_seats or inputs.current_route_avg_seats
    if (
        demand_growth_ratio >= 0.18
        and share_gain >= 0.01
        and inputs.current_global_od_flights >= 8
        and seat_proxy <= 195
        and (yield_proxy == 0.0 or yield_proxy >= 120.0)
    ):
        rationale.append("Predicted airline activity grows materially and market share also improves.")
        if yield_proxy > 0:
            rationale.append("Current web-price yield proxy is supportive, so larger-gauge capacity looks commercially defensible.")
        else:
            rationale.append("Route already shows enough market depth and current aircraft size proxy still looks narrow-body constrained.")
        return DecisionRecommendation("upgauge", _confidence(0.82, share_gain, demand_growth_ratio), rationale)

    if demand_growth_ratio >= 0.08 and share_gain >= -0.005:
        rationale.append("Predicted airline activity increases with at least stable share.")
        if yield_proxy > 0 and yield_proxy < 100.0:
            rationale.append("Observed web-price yield proxy is relatively soft, so adding frequency is safer than committing to larger capacity.")
        elif seat_proxy > 195:
            rationale.append("Current aircraft size proxy is already relatively large, so adding frequency is cleaner than further upgauging.")
        else:
            rationale.append("This supports adding frequency before committing to larger aircraft capacity.")
        return DecisionRecommendation("add frequency", _confidence(0.74, share_gain, demand_growth_ratio), rationale)

    if demand_growth_ratio <= -0.12 and share_gain < -0.01:
        rationale.append("Predicted airline activity falls and market share also deteriorates.")
        rationale.append("This suggests the route should not receive additional capacity in the next planning step.")
        return DecisionRecommendation("reduce / defend selectively", _confidence(0.79, share_gain, abs(demand_growth_ratio)), rationale)

    rationale.append("Predicted demand and share changes are not strong enough to justify a capacity move.")
    rationale.append("Maintain the current plan and wait for stronger market evidence.")
    return DecisionRecommendation("hold", _confidence(0.6, share_gain, abs(demand_growth_ratio)), rationale)


def _confidence(base: float, share_signal: float, growth_signal: float) -> float:
    bonus = min(max(abs(share_signal) * 4.0 + abs(growth_signal) * 0.5, 0.0), 0.18)
    return round(min(base + bonus, 0.95), 2)