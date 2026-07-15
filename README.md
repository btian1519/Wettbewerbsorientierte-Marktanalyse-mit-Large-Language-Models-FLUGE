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
   x            = Network Availability slider / 100            (0..1)
   net_factor F = 0.5 · (1 + sign(delta) · (2·x − 1))
   distance_eff = clamp(1 − |distance − 2000| / 10000, 0, 1)
   marge_proxy  = 0.5 · net_factor + 0.5 · distance_eff
   benefit(EUR) = delta · marge_proxy · marge_average · price_eur
   ```

   `net_factor` (F) makes the same slider act mirror-symmetrically on market gaps
   (delta > 0) and overcapacities (delta < 0); at delta = 0 it is a neutral 0.5.
   The slider therefore defaults to 100 % for opportunities and 0 % for
   overcapacities, both giving the neutral baseline F = 1.0.

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
* The demo generator targets ≥ 5 000 routes per scope. Honest data limits are
  handled rather than faked:
  * **Oceania** has only ~34 usable airports → ~1 100 valid directed pairs; all are
    generated (fewer than 5 000 is physically unavoidable without inventing
    airports).
  * ~290 airports in the source have no coordinates — these rows are dropped at
    load.
  * The source `Continent` column is unreliable (e.g. Alaskan airports tagged
    "Africa"), which used to create absurd ~17 000 km "intra-continental" routes.
    Each airport's continent is therefore **derived from its coordinates**
    (`shared/geo.py`) so route scopes and the map stay geographically consistent.
    ~100 of 967 airports are reclassified this way.
  * Degenerate O-D pairs (two airports of the same metro at identical
    coordinates, e.g. CMN/CAS in Casablanca) are rejected via a 100 km minimum
    route distance, so there are no 0 km routes.

## Configuration

Environment variables (all optional) override defaults in `shared/config.py`:

| Variable | Default | Purpose |
|---|---|---|
| `FLIGHTSCOPE_DB_URL` | `sqlite:///data/flightscope.db` | swap in PostgreSQL |
| `FLIGHTSCOPE_ROUTES_PER_CONTINENT` | `5000` | demo routes per scope |
| `FLIGHTSCOPE_INTERCONTINENTAL_ROUTES` | `5000` | demo intercontinental routes |
| `FLIGHTSCOPE_DEMO_SEED` | `42` | reproducibility |
| `FLIGHTSCOPE_LOG_LEVEL` | `INFO` | logging verbosity |

---

## Live-data integration (API layer)

An **additive** data platform runs *in parallel* with the demo data — the demo
tables, analysis engine and default behaviour are never changed. The analysis
reads only from the local database; the UI never calls an API.

```
External APIs → Connectors → Ingestion (sync) → Normalization → Database → Analysis → UI
```

### Setup

```bash
cp .env.example .env      # then fill in keys; .env is gitignored
# AIRLABS_API_KEY is the only key needed for the primary supply source.
```

Secrets are loaded from `.env` via `python-dotenv` in `shared/config.py` — **no
key is ever hard-coded**. Optional deps: `APScheduler` (scheduler), `pytrends`
(Google Trends).

### What's implemented vs prepared

| Source | Role | Status |
|---|---|---|
| **AirLabs** | primary supply (schedules) | implemented (real request/parse) |
| **OpenSky** | observed flights (validation) | implemented (arrivals) |
| **OpenFlights** | airport metadata | implemented (CSV parse) |
| **Aircraft DB** | type → seat capacity | implemented (lookup) |
| **Eurostat** | demand calibration | prepared (request layer ready) |
| **Amadeus** | price/availability | prepared (OAuth handshake ready) |
| **Google Trends** | demand proxy | prepared (uses pytrends if installed) |

Every connector inherits auth, retry+backoff, rate limiting, error mapping,
validation and logging from `ingestion/connectors/base.py`.

### Historical snapshots

New tables (`routes`, `supply_observations`, `demand_observations`,
`trend_observations`, `sync_runs`) carry `snapshot_date` / `week` / `valid_from` /
`valid_to` / `created_at` / `updated_at`, so every sync appends a snapshot and
trends (demand, capacity, market change) can be analysed later. `SupplyObservation`
and `DemandObservation` are read back as the same neutral `RouteRead` the engine
already consumes, so **the analysis engine is unchanged**.

### Global, UI-independent data pipeline

Data collection is a **separate process** from analysis and is **never** scoped to
the current UI selection:

* **Sync Now** (dev footer) and the scheduler update the *whole market* — all
  airports → all routes → all airlines per route — regardless of the selected
  airline/continent/task/filters.
* **Analyze** and **Refresh** only read/recompute from the local DB; they issue no
  API calls, so the UI stays fast.

A supply crawl seeds AirLabs with **every catalogued airport** as a departure
point (`coverage_scope = "Global"`; bound it with `SYNC_MAX_AIRPORTS` against rate
limits). A probe + circuit breaker abort fast during an outage instead of hanging.

Each run writes an append-only `SyncRun` (history) and upserts a `SyncState`
(latest coverage per source/category): `data_source`, `coverage_scope`,
`sync_status`, `sync_timestamp`. The dev footer separates **Analysis Status**
(what you're analysing) from **Data Status** (record counts, last sync, coverage).

### Background sync

`ingestion/scheduler` (APScheduler) runs per-source jobs — **supply** daily,
**demand** weekly, **metadata** monthly — each behaving exactly like "Sync Now"
(global, UI-independent). Opt-in via `FLIGHTSCOPE_SCHEDULER_AUTOSTART=1`.

### Data source switch

The dev footer has a **Demo / Live** switch (default **Demo**). Live mode reads
API-ingested snapshots and is empty until a sync populates it — demo data always
remains available and untouched.

### Live-platform env vars

| Variable | Default | Purpose |
|---|---|---|
| `AIRLABS_API_KEY` | – | AirLabs supply source (via `.env`) |
| `FLIGHTSCOPE_DATA_SOURCE` | `demo` | default read source (`demo`\|`live`) |
| `FLIGHTSCOPE_SCHEDULER_AUTOSTART` | `0` | auto-start background jobs |
| `SYNC_INTERVAL_SCHEDULES` / `_PRICES` / `_DEMAND` / `_AIRPORT_METADATA` | daily/daily/weekly/monthly | per-source sync frequency (seconds) |

---

## Demand Data Platform (V1, rule-based)

A transparent, versioned demand engine (no ML) that turns demand *signals* into a
standardized value per O-D route and week. Data flows one way and is never fetched
from the UI:

```
demand connectors → raw signals (stored) → normalization → model → calibration →
demand_normalized (stored) → get_weekly_demand() → analysis engine
```

**The analysis engine uses one function only** — `DemandService.get_weekly_demand(origin, destination, week)` → `(estimated_weekly_passengers, demand_index, confidence_score)`. It has no knowledge of Google Trends, Wikipedia, Eurostat or normalization.

### Sources (V1)
`ingestion/demand/`: **Google Trends** (short-term interest, needs `pytrends`),
**Wikipedia** pageviews (real Wikimedia API), **Eurostat** (calibration reference,
prepared), **World Bank** (population/GDP, prepared). Each reuses the resilient
connector base (retry, rate limit, error handling, logging, timestamps).

### Model — Demand Index V1
`0.45·Google + 0.15·Wikipedia + 0.15·Tourism + 0.10·Population + 0.10·GDP + 0.05·Event`
(each component normalized to 0–100). Missing sources → weights **dynamically
renormalized** over present components and confidence lowered. The model is
injected (`RuleBasedDemandModelV1` implements the `DemandModel` protocol), so an
ML forecaster drops in later with **no other change** — every row stores its
`calculation_version` + `snapshot_date` for history/training.

### Normalization (robust to outliers)
Per signal type, values are clipped to the 5th/95th percentiles across routes,
then min-max scaled to 0–100 — a single spiking route can't crush the rest.

### Calibration → passengers
`estimate = demand_index × calibration_factor` when a reference exists (Eurostat /
historical / demo). Otherwise a transparent gravity fallback (distance, airport
size, population, GDP) with a **lower confidence score**.

### Confidence score (0–1)
Rises with signal coverage, calibration and history: proxy-only ≈ **0.5**;
trends + reference + history ≈ **0.9+**.

### Tables & coverage
`demand_raw_signal`, `demand_normalized`, `demand_calibration` (additive; demo
untouched). The demand sync is **global** — it builds demand for all known routes
independent of any UI selection; the UI only filters. Recommended cadences:
Google/Wikipedia weekly, Eurostat monthly, macro yearly. The dev footer shows a
**Demand Status** panel (last sync, O-D pairs, signal count, source status, last
calculation version, average confidence).
