"""Schema migrations.

For the SQLite demo we create the schema directly via
:func:`database.base.create_all` and apply small, idempotent additive-column
migrations (``ALTER TABLE ... ADD COLUMN``) so an existing database picks up new
nullable columns without a full rebuild. This package is the designated home for
an Alembic environment once the project moves to PostgreSQL — where these
additive changes would be proper versioned migrations.
"""

from __future__ import annotations

from database.base import create_all, drop_all, get_engine
from shared.logging_config import get_logger

log = get_logger("database.migrations")

# Additive, nullable columns introduced after a table's first release. Keeps an
# existing SQLite DB forward-compatible without dropping data.
_ADDITIVE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "sync_runs": [("coverage_scope", "VARCHAR(32)")],
}


def _apply_additive_columns() -> None:
    engine = get_engine()
    if engine.dialect.name != "sqlite":
        return  # PostgreSQL uses Alembic (see module docstring)
    with engine.begin() as conn:
        for table, columns in _ADDITIVE_COLUMNS.items():
            try:
                existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            except Exception:  # noqa: BLE001 - table may not exist yet
                continue
            if not existing:
                continue
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                    log.info("Migration: added column %s.%s", table, name)


def initialize_schema() -> None:
    """Create all tables if missing, then apply additive-column migrations."""
    create_all()
    _apply_additive_columns()


def reset_schema() -> None:
    """Drop and recreate all tables. Destructive — used by the seed CLI."""
    drop_all()
    create_all()
