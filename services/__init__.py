"""UI-facing service layer for the FlightScope Streamlit frontend.

This package is the *only* bridge between the Streamlit UI (``ui/``,
``streamlit_app.py``) and the isolated backend (``flightscope_backend/`` →
repo ``src/``). The UI never imports the backend directly; it goes through
``analysis_service`` so that all backend adaptation, task filtering and
map-geometry enrichment live in one place.

Layers:
    ui/            – presentation only (Streamlit widgets, layout)
    services/      – this facade: adapts backend output into typed UI models
    flightscope_backend/ – isolated backend orchestration (no UI)
    src/           – original business logic / data access (unchanged)
"""
