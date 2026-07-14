"""Demand connector interface.

Every demand connector reuses the resilient HTTP plumbing of
:class:`~ingestion.connectors.base.BaseConnector` (auth, retry+backoff, rate
limiting, error mapping, logging) and additionally implements this small
interface: given a route + week, return typed :class:`RawSignal` records tagged
with their ``signal_type``, ``source`` and ``timestamp``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ingestion.demand.records import RawSignal, RouteContext


@runtime_checkable
class DemandConnector(Protocol):
    #: Raw signal type this connector emits (e.g. "google_trends").
    signal_type: str

    def available(self) -> bool:
        """Whether the connector can run (deps/credentials present)."""

    def fetch(self, ctx: RouteContext, week: str) -> list[RawSignal]:
        """Fetch raw demand signals for one route/week (empty list on soft failure)."""
