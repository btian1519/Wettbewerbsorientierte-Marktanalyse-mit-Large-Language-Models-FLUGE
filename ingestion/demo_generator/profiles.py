"""Economic heuristics for the demo generator.

These functions turn structural facts (airport masses, distance) into plausible
demand, capacity and pricing. They are deliberately parameterised and side-effect
free so the "realism knobs" live in one place and can be tuned or replaced when a
real calibration dataset becomes available.
"""

from __future__ import annotations

import numpy as np


def airport_masses(n: int, hub_flags: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Assign a gravity 'mass' to each airport.

    Hubs receive a large multiplier; every airport gets multiplicative lognormal
    noise so the network is not perfectly regular.
    """
    base = np.ones(n)
    hub_boost = rng.uniform(4.0, 9.0, size=n)
    base = np.where(hub_flags, base * hub_boost, base)
    noise = np.exp(rng.normal(0.0, 0.5, size=n))
    return np.maximum(0.05, base * noise)


def weekly_demand(mass_o: float, mass_d: float, distance_km: float, rng: np.random.Generator) -> int:
    """Gravity-style weekly passenger demand for a directed route."""
    gravity = (mass_o * mass_d) ** 0.5
    distance_decay = (2000.0 / (distance_km + 1500.0)) ** 0.30
    base = 780.0 * gravity * distance_decay
    demand = base * float(np.exp(rng.normal(0.0, 0.42)))
    return int(max(40.0, demand))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def served_probability(demand: int, hubness: float) -> float:
    """Probability that at least one airline operates a route.

    High-demand and hub-connected routes are more likely served, but the ceiling
    stays below 1 so that *some* high-demand routes remain unserved — those are
    exactly the 'market gap' opportunities the tool should surface.
    """
    p = 0.42 + 0.48 * _sigmoid((demand - 900) / 1300.0) + 0.10 * hubness
    return float(np.clip(p, 0.18, 0.90))


def num_airlines(demand: int, hubness: float, max_candidates: int, rng: np.random.Generator) -> int:
    """How many carriers compete on a served route."""
    expected = 1.0 + demand / 4200.0 + 1.4 * hubness
    n = int(np.clip(round(rng.normal(expected, 0.7)), 1, max(1, max_candidates)))
    return min(n, max_candidates)


def supply_ratio(rng: np.random.Generator) -> float:
    """Total capacity / demand. Median < 1 ⇒ a healthy mix of under- and
    over-served routes (opportunities vs. overcapacity)."""
    return float(np.exp(rng.normal(-0.05, 0.55)))


def seats_for_distance(distance_km: float, rng: np.random.Generator) -> int:
    """Typical seats per flight, widening with stage length (narrow→widebody)."""
    if distance_km < 1500:
        low, high = 150, 189
    elif distance_km < 4000:
        low, high = 180, 260
    else:
        low, high = 250, 360
    return int(rng.integers(low, high + 1))


def price_for_distance(distance_km: float, airline_index: float, rng: np.random.Generator) -> float:
    """Average one-way fare in EUR: a distance base × carrier premium × noise."""
    base = 48.0 + 0.072 * distance_km
    noise = float(np.exp(rng.normal(0.0, 0.14)))
    return round(max(29.0, base * airline_index * noise), 2)
