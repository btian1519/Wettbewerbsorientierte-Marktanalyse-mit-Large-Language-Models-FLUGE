"""Dependency wiring for the FlightScope backend.

Structural extraction of the import / module-reload block from the original
apps/app_flightscope_unified.py. The import-time reload of the ``src`` modules
and the BASE_DIR / PROCESSED_DIR resolution are preserved unchanged.

This module lives one directory below the repository root (like the original
apps/ file), so ``Path(__file__).parent.parent`` resolves to the same repo root
and ``src`` remains importable exactly as before.
"""

import importlib
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import src.collect_sources as collect_sources
from src.route_database import get_od_by_airline_homebase, get_od_candidate_pool_info
import src.route_database as route_database
import src.recommendation_engine as recommendation_engine


importlib.invalidate_caches()
collect_sources = importlib.reload(collect_sources)
route_database = importlib.reload(route_database)
recommendation_engine = importlib.reload(recommendation_engine)
CollectConfig = collect_sources.CollectConfig
collect_once = collect_sources.collect_once
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
