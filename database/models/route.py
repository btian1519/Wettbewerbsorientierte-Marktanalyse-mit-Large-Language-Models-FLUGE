"""Weekly route supply/demand model.

The schema is normalised into two tables so that new demand proxies or extra
per-airline attributes can be added later without touching existing columns:

* :class:`RouteWeek`   — one row per (week, origin, destination); holds the
  route-level, airline-independent facts: distance, market scope and total
  weekly passenger **demand**.
* :class:`AirlineOffer` — one row per (route-week, airline); holds each carrier's
  **supply**: seats, frequency, resulting weekly capacity and average price.

Total supply of a route = sum of ``capacity`` over its offers. Keeping demand on
the route (not the offer) is what lets us represent *unserved* routes (demand but
zero offers) and *overcapacity* routes (supply far above demand).
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class RouteWeek(Base):
    __tablename__ = "route_weeks"
    __table_args__ = (
        UniqueConstraint("week", "origin_iata", "dest_iata", name="uq_route_week"),
        Index("ix_route_week_scope", "week", "scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week: Mapped[str] = mapped_column(String(8), nullable=False)  # ISO year-week, e.g. 2026-W27

    origin_iata: Mapped[str] = mapped_column(ForeignKey("airports.iata"), nullable=False, index=True)
    dest_iata: Mapped[str] = mapped_column(ForeignKey("airports.iata"), nullable=False, index=True)

    origin_continent: Mapped[str] = mapped_column(String(32), nullable=False)
    dest_continent: Mapped[str] = mapped_column(String(32), nullable=False)
    # Market scope used for filtering: a continent name for intra-continental
    # routes, or "Global/Intercontinental" when the endpoints differ.
    scope: Mapped[str] = mapped_column(String(32), nullable=False)

    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    total_demand: Mapped[float] = mapped_column(Float, nullable=False)  # weekly passengers

    offers: Mapped[list["AirlineOffer"]] = relationship(
        back_populates="route", cascade="all, delete-orphan", lazy="selectin"
    )


class AirlineOffer(Base):
    __tablename__ = "airline_offers"
    __table_args__ = (
        UniqueConstraint("route_week_id", "airline_iata", name="uq_offer"),
        Index("ix_offer_airline", "airline_iata"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_week_id: Mapped[int] = mapped_column(
        ForeignKey("route_weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    airline_iata: Mapped[str] = mapped_column(ForeignKey("airlines.iata"), nullable=False)

    seats_per_flight: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)  # flights per week
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)  # seats_per_flight * frequency
    avg_price_eur: Mapped[float] = mapped_column(Float, nullable=False)

    route: Mapped["RouteWeek"] = relationship(back_populates="offers")
