# FlightScope AI — Projektübersicht

> **Zweck dieses Dokuments:** Dauerhafte Wissensbasis über Architektur, Datenfluss
> und Funktionalität von FlightScope AI. Es dient als Orientierung für zukünftige
> Entwicklungsaufgaben. Dieses Dokument beschreibt den *Ist-Zustand* — es ändert
> keinen Code.

FlightScope AI ist eine **Supply-vs-Demand-Analyse für den Passagierluftverkehr**.
Die App vergleicht wöchentliche Streckennachfrage mit der Sitzplatzkapazität der
Airlines und liefert zwei Sichten, jeweils nach monetärem Nutzen gerankt:

- **„Find new opportunities"** — unbediente/unterversorgte Marktlücken (Market Gaps).
- **„Identify overcapacities"** — Überkapazitäten im eigenen Netz der Airline.

Technologie-Stack: **Python 3.11+, Streamlit (UI), SQLAlchemy + SQLite (Persistenz),
pandas/numpy (Datenaufbereitung), Pydantic (Eingabe-DTOs), HTML5-Canvas (Karte)**.

---

## 1. Architekturübersicht

Die Anwendung folgt einer **strikten Schichtentrennung** mit **Dependency Injection**.
Jede Schicht kennt nur die *Interfaces* (Python `Protocol`s) der darunterliegenden
Schicht. Der Composition Root ist [`backend/container.py`](backend/container.py).

```
┌─────────────────────────────────────────────────────────────────────┐
│  frontend/          Streamlit UI (pages, sidebar, components, maps)  │
│                     kennt nur die Backend-Services + DTOs            │
├─────────────────────────────────────────────────────────────────────┤
│  backend/services/  Orchestrierung (Analysis / Catalog / Data /     │
│                     Demand) — der einzige Einstieg für das Frontend  │
├─────────────────────────────────────────────────────────────────────┤
│  backend/analysis, pricing, ranking, filters                        │
│                     reine, zustandslose Geschäftslogik              │
├─────────────────────────────────────────────────────────────────────┤
│  database/repository/   Protocol-Verträge + SQLAlchemy-Impl.        │
│                     liefert NEUTRALE Read-Models (keine ORM-Objekte) │
├─────────────────────────────────────────────────────────────────────┤
│  database/models/   SQLAlchemy ORM (Demo-Tabellen + Live/History)   │
├─────────────────────────────────────────────────────────────────────┤
│  ingestion/         Master-Data-Loader, Demo-Generator, Live-       │
│                     Connectors, Demand-Plattform, Scheduler         │
├─────────────────────────────────────────────────────────────────────┤
│  shared/            config, constants, geo, utils, logging          │
└─────────────────────────────────────────────────────────────────────┘
```

**Zentrale Architekturentscheidungen:**

1. **Repository liefert neutrale Read-Models** (`RouteRead`, `AirportRead`, …) als
   eingefrorene Dataclasses — die Analyse-Engine berührt nie eine lebende
   DB-Session, dadurch cache- und testbar.
2. **Persistenz hinter Protocols** + einer einzigen `db_url` in
   [`shared/config.py`](shared/config.py) → Wechsel SQLite → PostgreSQL ist eine
   Konfigurationsänderung.
3. **Zwei-Tabellen-Streckenschema** (`RouteWeek` + `AirlineOffer`): Nachfrage liegt
   auf der Strecke, Angebot pro Airline. Dadurch sind *unbediente* Strecken
   (Market Gaps) und *überversorgte* Strecken beide darstellbar.
4. **Zwei parallele Datenpfade** (Demo + Live), umschaltbar über
   `Container.analysis_for("demo"|"live")`. Die Demo-Daten werden vom Live-Pfad
   nie überschrieben.
5. **Custom-Canvas-Karte** statt PyDeck/Plotly, weil nur ein eigener
   `requestAnimationFrame`-Loop eine flüssige, von Streamlit-Reruns entkoppelte
   Flugzeug-Animation erlaubt.

---

## 2. Projektstruktur

| Verzeichnis / Datei | Aufgabe |
|---|---|
| [`app.py`](app.py) | Streamlit-Einstiegspunkt. Nur Bootstrap (DI-Container, Seeding) + Routing (Start-/Results-Page). |
| `AIRLINES.py` | **Einzige** Airline-Quelle (Python-Dict `AIRLINES`). |
| `AIRPORTS.xlsx` | **Einzige** Airport-Quelle (Excel). |
| `shared/` | Querschnitt: [`config.py`](shared/config.py) (Settings-Singleton, ENV), [`constants.py`](shared/constants.py) (Kontinente, Tasks, Modell-Defaults), [`geo.py`](shared/geo.py) (Kontinent aus Koordinaten), [`utils.py`](shared/utils.py) (haversine, clamp, Formatierung), `logging_config.py`, `rate_limit.py`, `sources.py`. |
| `database/models/` | ORM: `airport.py`, `airline.py`, [`route.py`](database/models/route.py) (`RouteWeek`, `AirlineOffer` = Demo), [`history.py`](database/models/history.py) (`Route`, `SupplyObservation`, `DemandObservation`, `TrendObservation`, `SyncRun`, `SyncState` = Live), `demand.py` (`RawDemandSignal`, `DemandNormalized`, `DemandCalibration`). |
| `database/repository/` | [`interfaces.py`](database/repository/interfaces.py) (Read-Models + `Protocol`-Verträge), [`sqlalchemy_repo.py`](database/repository/sqlalchemy_repo.py) (Demo: Catalog + Route), [`observation_repo.py`](database/repository/observation_repo.py) (Live: Observation + LiveRoute), `demand_repo.py`. |
| `database/base.py` | Engine/Session-Factory (memoisiert), SQLite-PRAGMAs (WAL, FK). |
| `database/migrations/` | `initialize_schema()` (create_all + additive `ALTER TABLE`), `reset_schema()`. Alembic-Platzhalter für PostgreSQL. |
| `ingestion/master_data.py` | Lädt `AIRLINES.py` & `AIRPORTS.xlsx`; Kontinentkorrektur, Zellenbereinigung. |
| `ingestion/demo_generator/` | Synthetischer Hub-and-Spoke-Supply/Demand-Generator ([`generator.py`](ingestion/demo_generator/generator.py)) + `profiles.py` (Nachfrage-/Preis-/Sitzplatz-Kurven). |
| `ingestion/connectors/` | Live-Supply-Connectors (AirLabs, OpenSky, OpenFlights, Aircraft DB, Eurostat, Amadeus, Google Trends) auf gemeinsamer `base.py` (Auth, Retry, Rate-Limit, Circuit Breaker). |
| `ingestion/demand/` | Demand-Data-Platform V1 (Connectors: Google Trends, Wikipedia, Eurostat, World Bank; `model.py` = regelbasiertes V1). |
| `ingestion/normalization/` | `normalize_schedules` (Supply), `build_signal_scores` (Demand). |
| `ingestion/calibration/` | Demand-Index → Passagiere (Kalibrierung + Gravity-Fallback). |
| `ingestion/scheduler/` | APScheduler-Jobs (Supply täglich, Demand wöchentlich, Metadata monatlich). |
| `ingestion/sync_service.py` | Globale, UI-unabhängige Marktsynchronisation. |
| `backend/dto.py` | `FilterSettings`, `AnalysisRequest` (Pydantic-Inputs); `RouteResult`, `AnalysisResponse` (frozen dataclass Outputs). |
| `backend/analysis/` | [`engine.py`](backend/analysis/engine.py) (Benefit/Delta-Formel), `market.py` (Scope-Validierung). |
| `backend/pricing/` | `PriceResolver` (Preis-Prioritätskette). |
| `backend/ranking/` | `rank_scored` (Sortierung + Top-N). |
| `backend/filters/` | `apply_filters` (aktuell nur Distance-Efficiency-Schwelle). |
| `backend/services/` | `AnalysisService`, `CatalogService`, `DataService`, `DemandService`. |
| `backend/container.py` | Composition Root (verdrahtet alle Implementierungen). |
| `frontend/pages/` | `start_page.py`, `results_page.py`. |
| `frontend/sidebar/` | `sidebar.py`, `dev_footer.py` (System Diagnostics), `diagnostics.py` (gecachter Snapshot). |
| `frontend/components/` | `inputs.py` (3 Dropdowns), `result_card.py` (Ergebniskarte). |
| `frontend/maps/` | `map_renderer.py` (`MapRenderer`-Protocol + `CanvasMapRenderer`), `map_html.py` (HTML/JS-Canvas). |
| `frontend/export/` | `pdf_export.py` (druckoptimierter PDF-Export). |
| `frontend/state.py` | Kapselung von `st.session_state` (Undo, Filter, Network-Availability). |
| `frontend/styles.py`, `theme.py` | CSS-Injektion, Farbpalette. |
| `assets/world_countries.json` | Vereinfachte Welt-GeoJSON (offline Karte). |
| `scripts/seed.py` | CLI zum (Neu-)Aufbau der Demo-Datenbank (`python -m scripts.seed --force`). |
| `data/flightscope.db` | Persistente SQLite-Datenbank (mit WAL-Dateien). |
| `tests/` | Unit- + Integrationstests (pytest). |

---

## 3. Datenfluss

### 3.1 Demo-Pfad (Standard — was der Nutzer sieht)

```
AIRLINES.py  +  AIRPORTS.xlsx
        │  (FileMasterDataSource: laden, bereinigen, Kontinent aus Koordinaten)
        ▼
   CatalogRepository  (airports, airlines Tabellen)
        │
        ▼
   DemoDataSource.produce(week)   ← seeded RNG (reproduzierbar)
        │  Hub-and-Spoke-Sampling, Nachfrage/Kapazität/Preis aus profiles.py
        ▼
   RouteRepository.bulk_load   (route_weeks + airline_offers)
        │   [einmalig; persistent — beim ersten Start automatisch]
        ▼
   AnalysisService.analyze(AnalysisRequest)
        │   query → filter → price → score → rank → to_result
        ▼
   AnalysisResponse (list[RouteResult] + stats)
        │
        ▼
   Streamlit results_page:  Karte  +  Ergebniskarten  +  PDF-Export
```

**Wichtig:** Das Seeding passiert **einmalig** und wird persistiert. `analyze` und
`Refresh` lesen/rechnen nur aus der lokalen DB — **kein** API-Aufruf zur Laufzeit.

### 3.2 Live-Pfad (additiv, parallel, standardmäßig leer)

```
Externe APIs → Connectors → SyncService (global) → Normalization → History-Tabellen
                                                                          │
                              DemandService.get_weekly_demand ────────────┤
                                                                          ▼
                              SqlAlchemyLiveRouteRepository → RouteRead → dieselbe AnalysisService
```

Der Live-Pfad schreibt in **separate** Tabellen (`routes`, `*_observations`, …)
und wird über den **Demo/Live-Schalter** im Dev-Footer ausgewählt
(`Container.analysis_for(source)`). Die Analyse-Engine ist für beide Pfade
**identisch**, weil beide Repositories dasselbe `RouteRead` liefern.

---

## 4. Datenmodell

### 4.1 Master-Daten (Katalog)

| Modell | Schlüsselfelder | Bemerkung |
|---|---|---|
| `Airport` | `iata` (PK), name, city, country, lon, lat, `continent` | Kontinent aus Koordinaten abgeleitet (nicht aus der Datei). |
| `Airline` | `iata` (PK), name, base, region, `base_iata` | `base_iata` aus dem Base-Feld extrahiert. |

### 4.2 Demo-Fakten (die eigentliche Analyse-Grundlage)

| Modell | Beziehung | Felder |
|---|---|---|
| `RouteWeek` | 1 Zeile pro (week, origin, dest) | scope, distance_km, **total_demand** (streckenweit, airline-unabhängig). |
| `AirlineOffer` | N pro RouteWeek (1 pro Airline) | seats_per_flight, frequency, **capacity**, avg_price_eur. |

`total_supply` einer Strecke = Σ `capacity` über die Offers.
Nachfrage auf der *Strecke* (nicht dem Offer) → unbediente Strecken (Demand > 0,
0 Offers) und Überkapazität (Supply ≫ Demand) sind beide abbildbar.

### 4.3 Live/History-Tabellen (additiv)

`Route` (kanonische O-D), `SupplyObservation`, `DemandObservation`,
`TrendObservation`, `SyncRun` (Append-only-Audit), `SyncState` (aktuelle Coverage
pro Quelle/Kategorie). Alle mit Zeitdimension (`snapshot_date`, `week`,
`valid_from/to`, `created_at/updated_at`) für spätere Trendanalysen.
**Keine harten Foreign Keys** auf Master-Daten — eine Live-Quelle darf Airports
referenzieren, bevor sie katalogisiert sind.

### 4.4 Demand-Plattform V1

`RawDemandSignal` (Rohsignale), `DemandNormalized` (0–100-Scores + Index +
Passagierschätzung + Confidence + `calculation_version`), `DemandCalibration`.

### 4.5 Read-Models (Analyse-Kontrakt)

`AirportRead`, `AirlineRead`, `OfferRead`, `RouteRead` — eingefrorene Dataclasses.
`RouteRead` bietet berechnete Properties: `total_supply`, `num_airlines`,
`offer_for(iata)`.

### 4.6 Ergebnis-DTOs

`RouteResult` (eine Ergebniszeile inkl. `display_benefit`/`display_delta`, die im
Overcapacity-Modus Absolutwerte zeigen, während intern das Vorzeichen für das
Ranking erhalten bleibt) und `AnalysisResponse` (Liste + Stats + Titel).

### 4.7 Session State

Siehe **Abschnitt 7**.

---

## 5. Analyse-Engine

Zentrale Datei: [`backend/analysis/engine.py`](backend/analysis/engine.py).
Orchestrierung: [`AnalysisService.analyze`](backend/services/analysis_service.py).

### 5.1 Benefit-/Delta-Formel (pro gerichteter Strecke, pro Woche)

```
delta        = demand − total_supply
x            = Network-Availability-Slider / 100            (0..1)
net_factor F = 0.5 · (1 + sign(delta) · (2·x − 1))
distance_eff = clamp(1 − |distance − 2000| / 10000, 0, 1)
marge_proxy  = 0.5 · F + 0.5 · distance_eff
benefit_full = delta · marge_proxy · marge_average · price_eur
```

- **`network_availability_factor`** macht denselben Slider *spiegelsymmetrisch*:
  bei Market Gap (delta>0) und Überkapazität (delta<0) reagiert er gegensätzlich;
  bei delta=0 immer neutral F=0.5. Deshalb defaultet der Slider auf 100 % für
  Opportunities und 0 % für Overcapacities (beide → neutrale Baseline F=1.0).
- **`distance_efficiency`** hat ihr Maximum bei 2000 km (`DISTANCE_EFFICIENCY_PEAK_KM`)
  und fällt mit einer Spanne von 10000 km (`DISTANCE_EFFICIENCY_SPREAD_KM`) ab.

### 5.2 Market Gaps vs. Overcapacities

- **Opportunities:** alle Strecken im Scope, `benefit_full`/`delta_full` (ein
  Neueinsteiger würde die gesamte Lücke bedienen). Routen mit **negativem** Benefit
  (überversorgt) werden verworfen. Ranking **maximiert** Benefit.
- **Overcapacities:** nur die Strecken der gewählten Airline. Benefit **und** Delta
  werden auf den **proportionalen Angebotsanteil** der Airline reduziert
  (`airline_capacity / total_supply`). Ranking **minimiert** Benefit (negativster =
  schlimmste Überversorgung zuerst).

### 5.3 Ablauf in `AnalysisService.analyze`

1. `validate_scope` + Woche bestimmen (`latest_week`).
2. Routen laden: `routes_for_airline` (Overcapacity) bzw. `routes_by_scope`
   (Opportunity).
3. `PriceResolver` über den **vollen** In-Scope-Satz bauen.
4. `apply_filters` (Distance-Efficiency-Schwelle; aktuell 0.0 → No-Op).
5. Pro Route: Preis auflösen → `BenefitEngine.score`.
6. Opportunities: negative Benefits filtern.
7. `rank_scored` (Top-N = 10).
8. `_to_result` — Anreicherung mit Airport-Master-Daten → `RouteResult`.
9. `stats` (routes_considered, after_filters, returned, compute_ms).

### 5.4 Preis-Auflösung ([`PriceResolver`](backend/pricing/pricing.py))

Mandatierte Prioritätskette:
1. Ø-Preis der **gewählten** Airline auf der Strecke (`airline`).
2. Sonst Ø-Preis **anderer** Airlines auf der Strecke (`route_others`).
3. Sonst Ø-Preis der gewählten Airline über **ähnliche Distanzen** (±25 %) im Scope
   (`distance_proxy`; Fallback: nächste bepreiste Strecke).
4. Letztes Netz: Scope-weiter Mittelwert (`scope_mean`), sonst `unavailable` (0.0).

Die Quelle wird als Tag im UI/Dev-Footer sichtbar gemacht.

### 5.5 Filter

Aktuell **nur** die Mindest-Distance-Efficiency-Schwelle aktiv (Default 0.0). Die
Parameter `marge_average` und `network_availability` sind **keine** Filter, sondern
Formel-Eingaben (in der Engine angewandt). Die Struktur erlaubt weitere
Schwellen-Filter aus `FilterSettings.extra` als lokale Änderung.

---

## 6. Streamlit-UI

Routing in [`app.py`](app.py) über `st.session_state.page` (`"start"` | `"results"`).

| Komponente | Datei | Inhalt |
|---|---|---|
| **Startseite** | `pages/start_page.py` | Titel, 3 Dropdowns (Airline/Continent/Task), „ANALYZE!"-Button (deaktiviert bis alle Inputs gesetzt). |
| **Ergebnisseite** | `pages/results_page.py` | Titel, animierte Karte (oberes Drittel), „Recommended priorities", Ergebniskarten, Show more/less, PDF-Export. |
| **Sidebar** | `sidebar/sidebar.py` | Spiegelt die 3 Inputs, „Additional Filters" (collapsed), Undo/Clear, „REFRESH!", Dev-Footer. Kein Back-Button (per Vorgabe). |
| **Kartenkomponente** | `maps/` | Siehe Abschnitt 8. |
| **Show Details** | `components/result_card.py` | Expander mit Origin/Destination-Details, Distanz, Preis, Demand/Supply, Marktanteil, **Anzahl** aktiver Airlines (nie Namen — Vorgabe), Gap/Benefit. |
| **Dev Footer** | `sidebar/dev_footer.py` | „System Diagnostics": Systemstatus, Demo/Live-Schalter, externe Datenquellen, Sync-Steuerung, Kartenhöhe, Background-Jobs, Logs. |

**Kommunikation:** Beide Seiten erhalten den `Container` und lesen `response` aus
dem Session State. Die Ergebnisseite reicht die sichtbaren Routen an den
`MapRenderer`. Der Dev-Footer schreibt `data_source`, `map_height`,
`sync_on_refresh` in den Session State, die `sidebar._refresh` bzw. die
Results-Page konsumieren. Die drei Dropdowns (`components/inputs.py`) sind auf
Start-Seite und Sidebar **identisch** (keyed widgets → gemeinsamer Zustand).

---

## 7. State Management

Zentrale Datei: [`frontend/state.py`](frontend/state.py). Alle `st.session_state`-
Zugriffe sind hinter benannten Funktionen gekapselt.

**Schlüssel-Gruppen:**
- **Inputs (keyed widgets):** `airline`, `scope`, `task`, `sl_margin`, `sl_net`.
- **Analyse-Zustand:** `response`, `visible` (Show-more-Zähler), `map_height`.
- **UI-Meta:** `net_customized` (hat der Nutzer den Network-Slider bewegt?).
- **Undo:** `current_snapshot`, `previous_snapshot`, `_pending_action`.

**Undo (genau eine Ebene, kein Redo):** Ein Snapshot umfasst Inputs + Analyse-
Zustand + Meta. Beim `Refresh` wird die zu ersetzende Analyse als `previous`
gesichert; Undo spielt `previous` **ohne Neuberechnung** zurück.

**Pending Actions:** Da der Wert eines keyed Widgets nach dessen Instanziierung
im selben Run nicht mehr geändert werden kann, registrieren Undo/Clear eine
*pending action*, die `apply_pending_action` **ganz oben im nächsten Run**
(vor jedem Widget) anwendet.

**Network Availability (Default vs. Nutzerwert):** Der Slider-Default ist
richtungsabhängig (100 % Opportunities / 0 % Overcapacities). Solange
`net_customized == False`, setzt `sync_network_availability` den Default bei jedem
Rerun neu (so aktualisiert ein Task-Wechsel den Wert); der `on_change`-Callback
`mark_net_customized` setzt das Flag auf True → danach bleibt der Nutzerwert
erhalten. `Clear All Filters` setzt zurück.

**Streamlit-Eigenheit:** Ein extern vorbelegter Session-State-Wert wird bei der
**ersten** Widget-Instanziierung ignoriert — daher liefert `filter_slider` den
Erst-Default über `value=` und lässt danach den Session State steuern.

**Show more/less:** Reine Anzeigeänderung über `visible` (3 ↔ bis 10). Es werden
**keine** neuen Ergebnisse berechnet; die Karte bleibt synchron, weil sie stets
`response.results[:visible]` rendert.

**Refresh** = Neuberechnung aus der DB (+ optional Sync davor, wenn
`sync_on_refresh` gesetzt). **Analyze** (Start-Seite) = Erstberechnung, kein
`previous` → Undo bleibt deaktiviert.

---

## 8. Kartenarchitektur

Datei: [`frontend/maps/map_renderer.py`](frontend/maps/map_renderer.py) +
[`map_html.py`](frontend/maps/map_html.py).

- **Bibliothek:** Kein Deck.gl/PyDeck/Plotly, sondern ein **eigener HTML5-Canvas-
  Renderer**. Begründung (README): PyDeck/Plotly rendern in Streamlit bei jedem
  Rerun statisch neu und können keinen kontinuierlichen Render-Loop treiben; eine
  Live-Basemap bräuchte Netzwerk-Tiles. Der `CanvasMapRenderer` läuft **offline**.
- **`MapRenderer`-Protocol:** Seam für einen späteren Deck.gl-Renderer ohne
  Änderung der Seiten.
- **Rendering-Strategie:** Die Welt (Ozean, Länder, alle Airport-Punkte,
  Streckenbögen, Endpunkte, Rang-Badges) wird **einmal** auf ein Offscreen-Canvas
  gezeichnet. Der `requestAnimationFrame`-Loop blittet nur dieses statische Canvas
  und zeichnet die bewegten Flugzeuge neu → **Kosten pro Frame = O(Routen)**,
  unabhängig vom Kartendetail. Der Loop ist von Streamlit-Reruns entkoppelt.
- **Flugrouten & Animation:** Quadratische Bézier-Bögen (nach oben gewölbt); jedes
  Flugzeug bewegt sich mit eigener Zufallsgeschwindigkeit entlang der Kurve und
  wird zur **Bézier-Tangente** rotiert (echter Kurs). Rotationsoffset über
  `AIRCRAFT_HEADING_OFFSET_DEG` justierbar.
- **View/Zoom:** Bounding-Box aus den Scope-Airports mit **2./98.-Perzentil**
  (robust gegen fehlplatzierte Airports), erweitert um die sichtbaren Routen-
  Endpunkte (`must_include`). Intercontinental → fixe Welt-Ansicht.
- **Layer/Performance:** Länder-Polygone werden **bbox-cullt** (nur was den View
  schneidet). GeoJSON + Bounding-Boxen werden per `lru_cache` einmal geladen. Die
  Kartenhöhe ist im Dev-Footer einstellbar (`map_height`).
- **Marker:** Alle Airports als kleine Punkte; Routen-Endpunkte hervorgehoben;
  Rang-Badge am Ziel.

---

## 9. Erweiterbarkeit

**Modularität / Trennung UI ↔ Backend:** Sehr gut. Das Frontend kennt nur die
Backend-Services und DTOs; Geschäftslogik (`analysis/pricing/ranking/filters`) ist
rein und zustandslos. Alle Austauschpunkte sind `Protocol`s + DI im Container.

**Empfohlene Integrationspunkte für zukünftige Features:**

| Feature | Ort |
|---|---|
| Alternativer Karten-Renderer (Deck.gl) | Neue Klasse hinter `MapRenderer`-Protocol in `frontend/maps/`. |
| Neue Filter | `backend/filters/filters.py` + `FilterSettings.extra`. |
| ML-Nachfrageprognose | `DemandModel`-Protocol implementieren, im Container injizieren — kein anderer Code ändert sich. |
| Neue Live-Datenquelle | Connector von `ingestion/connectors/base.py` ableiten, im Container registrieren. |
| PostgreSQL statt SQLite | `FLIGHTSCOPE_DB_URL` setzen; `database/migrations/` auf Alembic umstellen. |
| Weitere Streckenattribute | Additive Spalte + `database/migrations/_ADDITIVE_COLUMNS`. |
| Neue Analyse-Kennzahl | `BenefitEngine.score` / `ScoredRoute` / `RouteResult`. |

**Mögliche technische Schulden / Beobachtungen (nur Orientierung, keine Bugs):**

- **Distance-Efficiency-Filter-Slider** ist absichtlich nicht gerendert; der Wert
  läuft über den Default `DEFAULT_MIN_DISTANCE_EFFICIENCY = 0.0` (Filter faktisch
  inaktiv, aber jederzeit reaktivierbar).
- **`SHOW_MORE_RESULTS`** in `constants.py` wird nicht mehr direkt genutzt (die
  Show-more-Logik rechnet über `TOP_N_RESULTS`/`TOP_VISIBLE_RESULTS`).
- **Live-Pfad** ist teilweise „prepared" statt „implemented" (Eurostat, Amadeus,
  Google Trends je nach Keys/Deps) und standardmäßig leer, bis ein Sync läuft.
- **Demand-Coverage** ist absichtlich klein begrenzt (`DEMAND_MAX_AIRPORTS=15`,
  `DEMAND_MAX_ROUTES=50`) wegen Rate-Limits der Proxy-APIs.
- **Kontinent-Boxen** in `geo.py` sind grobe Rechtecke; Grenzfälle (±1–2°) sind
  unvermeidbar, für den Demo-Zweck aber unkritisch.

---

## 10. Bekannte TODOs / Prepared-Seams

- **Live-Connectors vervollständigen:** Eurostat (Demand-Kalibrierung), Amadeus
  (Preis/Verfügbarkeit), Google Trends (benötigt `pytrends`) sind als
  Request-Layer vorbereitet.
- **ML-Demand-Modell:** V1 ist regelbasiert (`RuleBasedDemandModelV1`); jede Zeile
  speichert `calculation_version` + `snapshot_date` für spätere Trainingsdaten.
- **Alembic-Migrationen** beim Wechsel auf PostgreSQL (heute additive
  `ALTER TABLE` nur für SQLite).
- **Scheduler** ist opt-in (`FLIGHTSCOPE_SCHEDULER_AUTOSTART=1`).

---

## 11. Betrieb / Kommandos

```bash
python -m pip install -r requirements.txt      # Abhängigkeiten (Python 3.11+)
python -m scripts.seed --force                 # Demo-DB neu aufbauen (optional)
streamlit run app.py                           # App starten
python -m pytest                               # Tests
```

Konfiguration ausschließlich über ENV-Variablen (siehe `.env.example` und
`shared/config.py`); Secrets über `.env` (gitignored), nie im Code.

---

*Erstellt als reine Analyse-/Dokumentationsaufgabe — es wurden keine Berechnungen,
keine UI, keine Datenbank und kein bestehender Code geändert.*
