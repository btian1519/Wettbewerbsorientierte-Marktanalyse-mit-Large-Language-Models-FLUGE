"""Streamlit presentation layer for FlightScope AI.

Modules:
    theme    – colour palette + injected CSS for the modernised look.
    state    – typed session-state keys and initialisation helpers.
    sidebar  – input controls (airline, continent, task, filters, refresh).
    map      – pydeck route map (arcs, airport markers, aircraft glyphs).
    results  – ranked recommendation cards with details / show-more.
    pages    – start page and results page composition.

The UI contains no business logic; it only reads user input, calls
``services.analysis_service`` and renders the returned typed models.
"""
