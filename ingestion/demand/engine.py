"""Deprecated — superseded by the Demand Data Platform V1.

The old multiplicative ``DemandEngine`` has been replaced by the transparent,
versioned :class:`~ingestion.demand.model.RuleBasedDemandModelV1` (additive
weighted formula + dynamic reweighting) and the :mod:`ingestion.calibration`
layer. Kept only as a pointer; import from :mod:`ingestion.demand.model` instead.
"""
