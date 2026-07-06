"""Schema migrations.

For the SQLite demo we create the schema directly via
:func:`database.base.create_all`. This package is the designated home for an
Alembic environment once the project moves to PostgreSQL — keeping migration
concerns isolated from the ORM models and repositories.
"""

from database.base import create_all, drop_all


def initialize_schema() -> None:
    """Create all tables if they do not yet exist (idempotent)."""
    create_all()


def reset_schema() -> None:
    """Drop and recreate all tables. Destructive — used by the seed CLI."""
    drop_all()
    create_all()
