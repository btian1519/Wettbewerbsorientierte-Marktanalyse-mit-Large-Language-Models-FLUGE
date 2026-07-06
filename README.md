# FlightScope AI

Supply-vs-demand analytics for passenger air travel. FlightScope AI compares
weekly route demand against carrier capacity and surfaces either **new market
opportunities** ("Find new opportunities") or **overcapacities** on an airline's
own network ("Identify overcapacities"), ranked by monetary benefit.

---

## Quick start

```bash
# 1. Install dependencies (Python 3.11+)
python -m pip install -r requirements.txt

# 2. Build the persistent demo database (~5 s, one-time)
python -m scripts.seed --force

# 3. Launch the app
streamlit run app.py
```

> On the first app launch the database is seeded automatically if empty, so
> step 2 is optional — it just lets you (re)build data from the CLI.

Run the tests with `python -m pytest`.

---

## What it does

1. Pick an **airline**, a **continent scope** and a **task** on the start page.
2. The backend compares demand and supply for every route in that market:

   ```
   delta        = demand − total_supply
   distance_eff = clamp(1 − |distance − 2000| / 10000, 0, 1)
   marge_proxy  = 0.5 · network_availability + 0.5 · distance_eff
   benefit(EUR) = delta · marge_proxy · marge_average · price_eur
   ```

   * **Opportunities** — all routes in scope, **maximise** benefit (biggest
     untapped market gaps first).
   * **Overcapacities** — only the selected airline's routes, **minimise**
     benefit; benefit & delta are reduced to the airline's *proportional* supply
     share.

3. The results page shows the top 3 (→ up to 10 via *Show more*) on an animated
   map plus detail cards, and can export a print-optimised **PDF**.

**Price (EUR)** is resolved with the mandated priority chain: selected airline on
the route → other airlines on the route → the airline's average over similar
distances in the same scope (final safety net: scope mean).

---

## Architecture

Strict separation of UI, business logic, data access and data models. Each layer
depends only on the interfaces of the layer below (dependency injection wired in
`backend/container.py`), which is what makes the system extensible.

```
app.py                       Streamlit entry point (routing only)

shared/                      config, constants, logging, pure utils
database/
  models/                    SQLAlchemy ORM (Airport, Airline, RouteWeek, AirlineOffer)
  repository/                Protocol contracts + SQLAlchemy impl (returns neutral read-models)
  migrations/                schema init (Alembic-ready seam)
ingestion/
  master_data.py             loads AIRLINES.py & AIRPORTS.xlsx (the ONLY data sources)
  demo_generator/            hub-and-spoke synthetic supply/demand
  api_interfaces/            prepared (not implemented) live-data seams
backend/
  dto.py                     request/response contracts
  analysis/                  benefit/delta engine + market scoping
  pricing/ ranking/ filters/ the analysis sub-steps
  services/                  catalog / data / analysis orchestration
  container.py               composition root (DI)
frontend/
  pages/ components/ sidebar/ maps/ export/   Streamlit UI
assets/                      simplified world GeoJSON for the map
tests/                       unit + integration tests
```

### Key design decisions

* **Repository returns plain read-models**, not ORM objects — the analysis engine
  never touches a live session, so results are safe to cache and easy to test.
* **Persistence is abstracted behind Protocols** and a single connection URL in
  `shared/config.py`; moving SQLite → PostgreSQL is a config change.
* **Ingestion is behind Protocols** (`MasterDataSource`, `SupplyDemandSource`);
  the demo generator and the (future) live APIs are interchangeable.
* **Two-table route schema** (`RouteWeek` + `AirlineOffer`) keeps demand
  route-level so unserved routes (market gaps) and overcapacity routes are both
  representable, and new per-carrier or per-week attributes can be added without
  migrations.

### Map: why a custom Canvas renderer

The brief asked for *smooth, frame-based* airplane animation and ranked
Deck.gl → PyDeck → Plotly. Inside Streamlit, PyDeck/Plotly re-render statically on
each rerun and can't drive a continuous render loop, while a live basemap needs
network tiles. The chosen `CanvasMapRenderer`:

* runs a real `requestAnimationFrame` loop, **decoupled from Streamlit reruns**;
* draws the world **once** to an offscreen canvas and only redraws the moving
  planes each frame → per-frame cost is O(routes), so it scales;
* rotates each plane to its Bézier-tangent (true heading);
* works **offline** (bundled, simplified world GeoJSON — matches the stylised look
  of the mockups).

It sits behind a `MapRenderer` Protocol, so a Deck.gl renderer can be dropped in
later without touching the pages.

---

## Data & constraints

* **Airlines** come exclusively from `AIRLINES.py`; **airports** exclusively from
  `AIRPORTS.xlsx`. None are hard-coded.
* Continents used: Africa, North America, South America, Europe, Asia, Oceania,
  plus the **Global/Intercontinental** scope (endpoints on different continents).
* The demo generator targets ≥ 5 000 routes per scope. Two honest data limits are
  handled rather than faked:
  * **Oceania** has only ~35 usable airports → max 1 190 directed pairs; all are
    generated (fewer than 5 000 is physically unavoidable without inventing
    airports).
  * ~290 airports in the source have no coordinates and a few have a continent
    label inconsistent with their coordinates. Coordinate-less rows are dropped at
    load; the map view uses percentile clipping so the odd mislabelled airport
    can't distort the continent zoom.

## Configuration

Environment variables (all optional) override defaults in `shared/config.py`:

| Variable | Default | Purpose |
|---|---|---|
| `FLIGHTSCOPE_DB_URL` | `sqlite:///data/flightscope.db` | swap in PostgreSQL |
| `FLIGHTSCOPE_ROUTES_PER_CONTINENT` | `5000` | demo routes per scope |
| `FLIGHTSCOPE_INTERCONTINENTAL_ROUTES` | `5000` | demo intercontinental routes |
| `FLIGHTSCOPE_DEMO_SEED` | `42` | reproducibility |
| `FLIGHTSCOPE_LOG_LEVEL` | `INFO` | logging verbosity |
