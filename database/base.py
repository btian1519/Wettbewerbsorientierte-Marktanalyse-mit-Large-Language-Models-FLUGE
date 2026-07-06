"""SQLAlchemy engine, session factory and declarative base.

Engine creation is centralised and memoised. ``SQLite`` gets a couple of
pragmatic PRAGMAs (WAL + foreign keys) so it behaves well under the read-heavy
Streamlit access pattern; those hooks are no-ops on other back-ends.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.config import Settings, get_settings
from shared.logging_config import get_logger

log = get_logger("database.base")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings: Settings = get_settings()
    is_sqlite = settings.db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(
        settings.db_url,
        echo=settings.sql_echo,
        future=True,
        connect_args=connect_args,
    )
    if is_sqlite:
        _install_sqlite_pragmas(engine)
    log.debug("Engine created for %s", settings.db_url)
    return engine


def _install_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context manager."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all() -> None:
    """Create tables for all registered models (idempotent)."""
    # Import side-effect: ensure models are registered on ``Base.metadata``.
    from database import models  # noqa: F401

    Base.metadata.create_all(get_engine())


def drop_all() -> None:
    from database import models  # noqa: F401

    Base.metadata.drop_all(get_engine())
