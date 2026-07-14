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

# Load a local .env (if present) so secrets/keys never live in code. Safe no-op
# when python-dotenv is absent or the file is missing.
try:  # pragma: no cover - trivial import guard
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:  # pragma: no cover
    pass


def _env_opt(name: str) -> str | None:
    """Optional environment variable (None when unset/empty)."""
    raw = os.environ.get(name)
    return raw if raw not in (None, "") else None


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
    # Default data source the analysis reads from: "demo" | "live". The UI can
    # override this per session; demo stays the default and is never overwritten.
    default_data_source: str = field(default_factory=lambda: _env_str("FLIGHTSCOPE_DATA_SOURCE", "demo"))

    # --- External API credentials (loaded from env/.env; never hard-coded) --
    airlabs_api_key: str | None = field(default_factory=lambda: _env_opt("AIRLABS_API_KEY"))
    opensky_client_id: str | None = field(default_factory=lambda: _env_opt("OPENSKY_CLIENT_ID"))
    opensky_client_secret: str | None = field(default_factory=lambda: _env_opt("OPENSKY_CLIENT_SECRET"))
    amadeus_client_id: str | None = field(default_factory=lambda: _env_opt("AMADEUS_CLIENT_ID"))
    amadeus_client_secret: str | None = field(default_factory=lambda: _env_opt("AMADEUS_CLIENT_SECRET"))
    # Eurostat and Google Trends need no API key.

    # --- Background sync frequencies (seconds) per source category ----------
    # Defaults follow the brief: airport metadata monthly, schedules daily,
    # prices daily, demand proxies weekly. Each is env-overridable.
    sync_interval_airport_metadata: int = field(
        default_factory=lambda: _env_int("SYNC_INTERVAL_AIRPORT_METADATA", 30 * 24 * 3600))
    sync_interval_schedules: int = field(
        default_factory=lambda: _env_int("SYNC_INTERVAL_SCHEDULES", 24 * 3600))
    sync_interval_prices: int = field(
        default_factory=lambda: _env_int("SYNC_INTERVAL_PRICES", 24 * 3600))
    sync_interval_demand: int = field(
        default_factory=lambda: _env_int("SYNC_INTERVAL_DEMAND", 7 * 24 * 3600))
    # Whether the APScheduler background scheduler should auto-start with the app.
    scheduler_autostart: bool = field(
        default_factory=lambda: os.environ.get("FLIGHTSCOPE_SCHEDULER_AUTOSTART") == "1")
    # Upper bound on departure airports crawled per supply sync (0 = all = full
    # market / "Global" coverage). The sync is deliberately independent of any UI
    # selection; this only bounds request volume against API rate limits.
    sync_max_airports: int = field(default_factory=lambda: _env_int("SYNC_MAX_AIRPORTS", 0))
    # Demand coverage is built independently of supply, directly from the AIRPORTS
    # catalog. Bounded because demand proxies (e.g. Google Trends) are heavily
    # rate-limited: pool of airports for O-D generation, and a cap on total pairs.
    demand_max_airports: int = field(default_factory=lambda: _env_int("DEMAND_MAX_AIRPORTS", 15))
    demand_max_routes: int = field(default_factory=lambda: _env_int("DEMAND_MAX_ROUTES", 50))

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
