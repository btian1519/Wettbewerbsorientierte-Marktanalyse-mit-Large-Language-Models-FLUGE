"""Business logic layer.

Organised by responsibility: ``analysis`` (the benefit/delta model), ``pricing``
(fare resolution), ``ranking`` (top-N selection), ``filters`` (user thresholds)
and ``services`` (orchestration). The public data contracts live in
:mod:`backend.dto`; wiring lives in :mod:`backend.container`.
"""
