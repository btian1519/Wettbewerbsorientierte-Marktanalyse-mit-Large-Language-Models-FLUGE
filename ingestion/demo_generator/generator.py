"""Demo supply/demand generator (implements ``SupplyDemandSource``).

Produces one ISO-week snapshot of realistic route data:

* **Structure** — mass-weighted sampling makes airline hubs appear far more often
  as endpoints, so a hub-and-spoke topology emerges naturally.
* **Economics** — demand, capacity and price come from :mod:`profiles`.
* **Signal** — a share of high-demand routes is left *unserved* (market gaps) and
  supply ratios are spread around 1.0 (over- vs. under-capacity).

Everything is driven by a single seeded RNG, so the dataset is reproducible.
"""

from __future__ import annotations

import itertools
from typing import Sequence

import numpy as np

from database.repository.interfaces import AirlineRead, AirportRead
from ingestion.demo_generator import profiles
from ingestion.interfaces import SupplyDemandBatch
from shared.config import Settings, get_settings
from shared.constants import AIRPORT_CONTINENTS, INTERCONTINENTAL
from shared.logging_config import get_logger
from shared.utils import haversine_km

log = get_logger("ingestion.demo_generator")

_HUB_FRACTION = 0.12  # extra random hubs on top of airline bases


class DemoDataSource:
    """Generates weekly route facts from the loaded master data."""

    def __init__(
        self,
        airports: Sequence[AirportRead],
        airlines: Sequence[AirlineRead],
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._airports = list(airports)
        self._airlines = list(airlines)
        # Global index arrays.
        self._n = len(self._airports)
        self._lat = np.array([a.lat for a in self._airports])
        self._lon = np.array([a.lon for a in self._airports])
        self._continent = [a.continent for a in self._airports]
        self._iata = [a.iata for a in self._airports]
        self._airlines_by_region: dict[str, list[str]] = {}
        for a in self._airlines:
            self._airlines_by_region.setdefault(a.region, []).append(a.iata)

    # ------------------------------------------------------------------ #
    def produce(self, week: str | None = None) -> SupplyDemandBatch:
        week = week or self._settings.demo_week
        rng = np.random.default_rng(self._settings.demo_seed)

        # Per-carrier price premium index (deterministic given the seed).
        price_index = {a.iata: float(rng.uniform(0.85, 1.18)) for a in self._airlines}

        # Global hub designation + masses.
        base_iatas = {a.base_iata for a in self._airlines if a.base_iata}
        hub_flags = np.array(
            [
                (self._iata[i] in base_iatas) or (rng.random() < _HUB_FRACTION)
                for i in range(self._n)
            ]
        )
        mass = profiles.airport_masses(self._n, hub_flags, rng)
        hub_ref = float(np.quantile(mass, 0.90)) or 1.0
        hubness = np.clip(mass / hub_ref, 0.0, 1.0)

        route_rows: list[dict] = []
        offer_rows: list[dict] = []
        route_ids = itertools.count(1)
        offer_ids = itertools.count(1)

        idx_by_continent: dict[str, np.ndarray] = {
            c: np.array([i for i in range(self._n) if self._continent[i] == c])
            for c in AIRPORT_CONTINENTS
        }

        # --- Intra-continental scopes -------------------------------------
        for cont in AIRPORT_CONTINENTS:
            indices = idx_by_continent[cont]
            if len(indices) < 2:
                continue
            candidates = self._airlines_by_region.get(cont, [])
            pairs = self._sample_intra_pairs(indices, mass, self._settings.routes_per_continent, rng)
            for oi, di in pairs:
                self._emit_route(
                    oi, di, cont, candidates, week, mass, hubness, price_index,
                    rng, route_rows, offer_rows, route_ids, offer_ids,
                )
            log.info("Scope %-22s -> %5d routes", cont, len(pairs))

        # --- Intercontinental scope ---------------------------------------
        inter_pairs = self._sample_inter_pairs(mass, self._settings.intercontinental_routes, rng)
        for oi, di in inter_pairs:
            candidates = list(
                dict.fromkeys(
                    self._airlines_by_region.get(self._continent[oi], [])
                    + self._airlines_by_region.get(self._continent[di], [])
                )
            )
            self._emit_route(
                oi, di, INTERCONTINENTAL, candidates, week, mass, hubness, price_index,
                rng, route_rows, offer_rows, route_ids, offer_ids,
            )
        log.info("Scope %-22s -> %5d routes", INTERCONTINENTAL, len(inter_pairs))

        log.info("Demo batch: %d routes, %d offers", len(route_rows), len(offer_rows))
        return SupplyDemandBatch(week=week, route_rows=route_rows, offer_rows=offer_rows)

    # ------------------------------------------------------------------ #
    # Route emission
    # ------------------------------------------------------------------ #
    def _emit_route(
        self, oi: int, di: int, scope: str, candidates: list[str], week: str,
        mass: np.ndarray, hubness: np.ndarray, price_index: dict[str, float],
        rng: np.random.Generator, route_rows: list[dict], offer_rows: list[dict],
        route_ids: itertools.count, offer_ids: itertools.count,
    ) -> None:
        distance = haversine_km(self._lat[oi], self._lon[oi], self._lat[di], self._lon[di])
        demand = profiles.weekly_demand(mass[oi], mass[di], distance, rng)
        route_hubness = float(max(hubness[oi], hubness[di]))

        route_id = next(route_ids)
        served = bool(candidates) and (rng.random() < profiles.served_probability(demand, route_hubness))

        if served:
            total_cap = profiles.supply_ratio(rng) * demand
            k = profiles.num_airlines(demand, route_hubness, len(candidates), rng)
            chosen = rng.choice(candidates, size=k, replace=False)
            shares = rng.dirichlet(np.ones(k)) if k > 1 else np.array([1.0])
            for airline_iata, share in zip(chosen, shares):
                seats = profiles.seats_for_distance(distance, rng)
                cap_target = max(float(seats), total_cap * float(share))
                frequency = max(1, int(round(cap_target / seats)))
                capacity = seats * frequency
                offer_rows.append(
                    {
                        "id": next(offer_ids),
                        "route_week_id": route_id,
                        "airline_iata": str(airline_iata),
                        "seats_per_flight": seats,
                        "frequency": frequency,
                        "capacity": capacity,
                        "avg_price_eur": profiles.price_for_distance(
                            distance, price_index[str(airline_iata)], rng
                        ),
                    }
                )

        route_rows.append(
            {
                "id": route_id,
                "week": week,
                "origin_iata": self._iata[oi],
                "dest_iata": self._iata[di],
                "origin_continent": self._continent[oi],
                "dest_continent": self._continent[di],
                "scope": scope,
                "distance_km": round(distance, 1),
                "total_demand": float(demand),
            }
        )

    # ------------------------------------------------------------------ #
    # Pair sampling
    # ------------------------------------------------------------------ #
    def _sample_intra_pairs(
        self, indices: np.ndarray, mass: np.ndarray, target: int, rng: np.random.Generator
    ) -> list[tuple[int, int]]:
        n = len(indices)
        max_pairs = n * (n - 1)
        target = min(target, max_pairs)
        mass_sub = mass[indices]

        if max_pairs <= int(target * 1.5):
            # Small scope: enumerate all directed pairs, then weight-sample down.
            all_pairs = [(int(a), int(b)) for a in indices for b in indices if a != b]
            if len(all_pairs) <= target:
                return all_pairs
            weights = np.array([mass[a] * mass[b] for a, b in all_pairs])
            weights /= weights.sum()
            picked = rng.choice(len(all_pairs), size=target, replace=False, p=weights)
            return [all_pairs[k] for k in picked]

        # Large scope: mass-weighted rejection sampling.
        p = mass_sub / mass_sub.sum()
        seen: set[tuple[int, int]] = set()
        pairs: list[tuple[int, int]] = []
        attempts, max_attempts = 0, target * 60
        while len(pairs) < target and attempts < max_attempts:
            block = min(8192, target * 2)
            oa = indices[rng.choice(n, size=block, p=p)]
            da = indices[rng.choice(n, size=block, p=p)]
            for a, b in zip(oa, da):
                key = (int(a), int(b))
                if a != b and key not in seen:
                    seen.add(key)
                    pairs.append(key)
                    if len(pairs) >= target:
                        break
            attempts += block
        return pairs

    def _sample_inter_pairs(
        self, mass: np.ndarray, target: int, rng: np.random.Generator
    ) -> list[tuple[int, int]]:
        p = mass / mass.sum()
        continent = self._continent
        seen: set[tuple[int, int]] = set()
        pairs: list[tuple[int, int]] = []
        attempts, max_attempts = 0, target * 80
        while len(pairs) < target and attempts < max_attempts:
            block = min(8192, target * 2)
            oa = rng.choice(self._n, size=block, p=p)
            da = rng.choice(self._n, size=block, p=p)
            for a, b in zip(oa, da):
                a, b = int(a), int(b)
                if a != b and continent[a] != continent[b] and (a, b) not in seen:
                    seen.add((a, b))
                    pairs.append((a, b))
                    if len(pairs) >= target:
                        break
            attempts += block
        return pairs
