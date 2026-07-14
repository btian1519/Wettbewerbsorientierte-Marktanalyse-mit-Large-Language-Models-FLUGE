"""Airport master data model.

Rows originate exclusively from ``AIRPORTS.xlsx`` (loaded by the ingestion
catalog). No airport is ever hard-coded.
"""

from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Airport(Base):
    __tablename__ = "airports"

    iata: Mapped[str] = mapped_column(String(3), primary_key=True)
    # ``name`` holds the airport name (mapped from the "Airport" column).
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(96), nullable=True)
    country: Mapped[str | None] = mapped_column(String(96), nullable=True)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    continent: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Airport {self.iata} ({self.continent})>"
