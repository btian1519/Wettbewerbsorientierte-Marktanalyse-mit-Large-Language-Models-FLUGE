# FlightScope AI — Streamlit Frontend

Modern Streamlit UI on top of the existing FlightScope backend. The UI is a
**frontend only**: all analysis runs through the existing backend logic via a
thin service layer.

## Architecture

```
streamlit_app.py            # entry point: page config, theme, routing
ui/                         # presentation only (no business logic)
    theme.py                #   palette + injected CSS
    state.py                #   typed session-state helpers
    sidebar.py              #   Airline / Continent / Task + Additional Filters + Refresh
    map.py                  #   pydeck route map (arcs, markers, aircraft glyph)
    results.py              #   ranked recommendation cards, Show more, Export
    pages.py                #   start page + results page composition
services/                   # UI ↔ backend facade
    models.py               #   typed dataclasses (AnalysisParams, Recommendation, …)
    geo.py                  #   IATA→coordinate table + map camera math
    analysis_service.py     #   runs backend, adapts payload, applies Task filter
flightscope_backend/        # isolated backend orchestration (from prior step)
src/                        # original business logic (UNCHANGED) — required at runtime
data/                       # raw/processed data read by the backend — required at runtime
```

**Data flow:** `ui/` → `services.analysis_service.run_analysis()` →
`flightscope_backend.services.planning.build_analysis()` → `src/…`. The UI never
imports `src/` or `flightscope_backend/` directly.

### Key design decisions

- **Task is a UI/service concept.** The backend has no "task" input, so
  `analysis_service` maps `Find new opportunities` / `Identify overcapacities`
  to a *soft* ordering over `market_opportunity_label`. Nothing is dropped, so
  the map and the list stay in sync.
- **Airport coordinates live in the frontend** (`services/geo.py`) because the
  backend stores none. Unknown codes are skipped on the map, never crash.
- **Show more without recompute:** one analysis computes up to 25 rows; the UI
  reveals them 3 at a time from session state. Map draws exactly the visible
  rows.
- **Runs without API keys or data:** analysis only *scores* existing data; it
  does not trigger collection. With no `data/raw`, the backend returns zero
  recommendations and the UI shows a helpful notice instead of failing.

## Requirements

`src/` and `data/` from the FlightScope repo must sit at the project root
(the backend package wraps them). Then:

```bash
pip install -r requirements-ui.txt   # streamlit, pydeck, pandas
streamlit run streamlit_app.py
```

## Extending

- **Add a filter:** add a control in `sidebar._render_additional_filters_placeholder`,
  store it via `state.Key.FILTERS`, and consume it in `analysis_service`.
- **Animate the aircraft:** replace `ui.map._aircraft_layer` with a deck.gl
  `TripsLayer`; no other module changes.
