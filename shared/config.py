"""Application configuration.

A single immutable :class:`Settings` object is resolved once at import time from
environment variables (with sensible defaults). Centralising configuration here
keeps file paths, the database URL and demo-generation parameters out of the
business logic, which is what makes a later switch to PostgreSQL or to live API
ingestion a one-line change rather than a refactor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# Project root = directory that contains this ``shared`` package's parent.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return raw if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration."""

    # --- Data source files (must not be moved; hard project constraint) -----
    airlines_file: Path = PROJECT_ROOT / "AIRLINES.py"
    airports_file: Path = PROJECT_ROOT / "AIRPORTS.xlsx"

    # --- Persistence --------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"
    # SQLAlchemy URL. Override with FLIGHTSCOPE_DB_URL to point at PostgreSQL.
    db_url: str = field(default_factory=lambda: _env_str(
        "FLIGHTSCOPE_DB_URL",
        f"sqlite:///{(PROJECT_ROOT / 'data' / 'flightscope.db').as_posix()}",
    ))
    sql_echo: bool = field(default_factory=lambda: os.environ.get("FLIGHTSCOPE_SQL_ECHO") == "1")

    # --- Demo data generation ----------------------------------------------
    # Target O-D routes per continent scope. Physically capped at the number of
    # available airport pairs (e.g. Oceania has far fewer than 5000 pairs).
    routes_per_continent: int = field(default_factory=lambda: _env_int("FLIGHTSCOPE_ROUTES_PER_CONTINENT", 5000))
    intercontinental_routes: int = field(default_factory=lambda: _env_int("FLIGHTSCOPE_INTERCONTINENTAL_ROUTES", 5000))
    demo_seed: int = field(default_factory=lambda: _env_int("FLIGHTSCOPE_DEMO_SEED", 42))
    demo_week: str = field(default_factory=lambda: _env_str("FLIGHTSCOPE_DEMO_WEEK", "2026-W27"))

    # --- Ingestion mode -----------------------------------------------------
    # "demo" | "api" — only "demo" is wired up; "api" is prepared via interfaces.
    ingestion_mode: str = field(default_factory=lambda: _env_str("FLIGHTSCOPE_INGESTION_MODE", "demo"))

    # --- Logging ------------------------------------------------------------
    log_level: str = field(default_factory=lambda: _env_str("FLIGHTSCOPE_LOG_LEVEL", "INFO"))

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
