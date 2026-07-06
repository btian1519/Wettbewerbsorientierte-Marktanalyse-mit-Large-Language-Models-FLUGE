"""Persistence layer: ORM models + repository abstraction.

The rest of the application talks to persistence only through the repository
*interfaces* (``database.repository.interfaces``). Concrete SQLAlchemy details
stay behind that boundary, so migrating from SQLite to PostgreSQL means changing
the connection URL in :mod:`shared.config` — nothing in the business code.
"""
