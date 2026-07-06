"""Centralised logging setup.

A tiny in-memory ring buffer handler is attached in addition to the console
handler so that the Streamlit *Dev Footer* can display the most recent log
records (error logs, calculation status) without touching the filesystem.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque

_CONFIGURED = False
_RING_CAPACITY = 200
_ring_buffer: Deque[logging.LogRecord] = deque(maxlen=_RING_CAPACITY)


class RingBufferHandler(logging.Handler):
    """Keep the last N log records in memory for UI inspection."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        _ring_buffer.append(record)


def configure_logging(level: str = "INFO") -> None:
    """Idempotently configure the root logger."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger("flightscope")
    root.setLevel(level.upper())
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    ring = RingBufferHandler()
    ring.setFormatter(fmt)
    root.addHandler(ring)

    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``flightscope`` namespace."""
    return logging.getLogger(f"flightscope.{name}")


def recent_logs(limit: int = 50, min_level: int = logging.INFO) -> list[str]:
    """Return the most recent formatted log lines (newest last)."""
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    records = [r for r in _ring_buffer if r.levelno >= min_level]
    return [fmt.format(r) for r in records[-limit:]]
