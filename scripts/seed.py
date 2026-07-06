"""CLI to (re)build the persistent demo database.

Usage (from the project root)::

    python -m scripts.seed          # seed only if empty
    python -m scripts.seed --force  # drop & regenerate everything
"""

from __future__ import annotations

import argparse
import time

from backend.container import build_container
from shared.logging_config import get_logger

log = get_logger("scripts.seed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the FlightScope AI database.")
    parser.add_argument("--force", action="store_true", help="Drop and regenerate all data.")
    args = parser.parse_args()

    container = build_container()
    t0 = time.perf_counter()
    if args.force:
        container.data_service.reseed()
    else:
        container.data_service.ensure_seeded()
    dt = time.perf_counter() - t0

    status = container.data_service.status()
    print(f"\nSeeding finished in {dt:.1f}s")
    print(f"  airports : {status['airports']}")
    print(f"  airlines : {status['airlines']}")
    print(f"  routes   : {status['routes']}")
    print(f"  offers   : {status['offers']}")
    print(f"  week     : {status['current_week']}")
    print("  routes by scope:")
    for scope, n in sorted(status["routes_by_scope"].items()):
        print(f"    {scope:<24} {n}")


if __name__ == "__main__":
    main()
