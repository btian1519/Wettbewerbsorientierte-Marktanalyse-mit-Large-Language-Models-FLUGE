"""Airline master data model.

Rows originate exclusively from ``AIRLINES.py``. No airline is ever hard-coded
in application logic.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Airline(Base):
    __tablename__ = "airlines"

    iata: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    base: Mapped[str] = mapped_column(String(96), nullable=False)
    region: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # IATA code of the home base airport, parsed from ``base`` (e.g. "MUC").
    base_iata: Mapped[str | None] = mapped_column(String(3), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Airline {self.iata} {self.name}>"
