# Session 2 Presentation Prep — Luftfahrt (Fluggesellschaften)
**Kurs**: Wettbewerbsorientierte Marktanalyse mit Large Language Models  
**Datum**: 30. April 2026 | **Dauer**: 10 Minuten pro Gruppe  
**Ziel**: Literaturgrundlage klaeren, Branche eingrenzen, erste Ideen fuer ein moegliches Tool entwickeln

---

## 1) Branchenwahl und Eingrenzung

### Gewaehlte Branche
**Kommerzieller Passagierflugverkehr in Europa mit Fokus auf Deutschland**

### Konkrete Eingrenzung (fuer die erste Projektphase)
- **Segment**: Kurz- und Mittelstrecke (Intra-Europa)
- **Anbieter-Typen**:
  - Network Carrier: Lufthansa, Air France, KLM
  - Low-Cost Carrier: Ryanair, easyJet, Wizz Air
  - Optionaler Vergleich: Eurowings (Hybrid/Freizeitfokus)
- **Kundenkontaktpunkte**: Buchung, Check-in, Boarding, Puenktlichkeit, Gepaeck, Service bei Stoerungen
- **Regionale Abgrenzung**: EU-/EWR-Markt, deutschsprachige Kundenperspektive

### Warum diese Eingrenzung sinnvoll ist
- Hohe Wettbewerbsdynamik zwischen Legacy und Low-Cost
- Sehr grosse Menge oeffentlich verfuegbarer Nutzerdaten (Trustpilot, App Reviews, X/Foren, Reddit)
- Klare, wiederkehrende Kundenprobleme (Verspaetung, Erstattung, Kundenservice)
- Gut geeignet fuer LLM-gestuetzte, dimensionsbasierte Wettbewerbsanalyse

---

## 2) Literaturgrundlage (aus den vorhandenen Papern)

### Paper A: Porter, Competitive Strategy
**Beitrag fuer unser Projekt**
- Strukturierung des Wettbewerbs ueber Five Forces
- Ableitung strategischer Unterschiede zwischen Netzwerk-Airlines und Low-Cost-Airlines

**Beispielhafte Anwendung auf Luftfahrt**
- Hohe Rivalitaet (Preis, Netz, Slots)
- Starke Verhandlungsmacht der Kunden (Preisvergleich sehr transparent)
- Hohe Eintrittsbarrieren (Slots, Flotte, Regulierung)

### Paper B: IPA + Kano (Review-basierte Leistungsanalyse)
**Beitrag fuer unser Projekt**
- Identifiziert, welche Leistungsmerkmale aus Kundensicht Basisanforderungen vs. Differenzierungsmerkmale sind

**Uebertragung auf Luftfahrt**
- Kano-Basisfaktoren: Sicherheit, Zuverlaessigkeit, transparente Gepaeckregeln
- Leistungsfaktoren: Puenktlichkeit, Preis-Leistung, Problemloesung bei Irregularitaeten
- Begeisterungsfaktoren: proaktive Umbuchung, kulante Entschaedigung, sehr gute App-Experience

### Paper C: LLM-Cure (LLM-basierte Konkurrenzanalyse aus Reviews)
**Beitrag fuer unser Projekt**
- Methodischer Kern: unstrukturierte Reviews in strukturierte Wettbewerbsdimensionen ueberfuehren
- Automatisierte Extraktion von Staerken/Schwaechen pro Anbieter
- Erstellung einer vergleichbaren Scorecard ueber mehrere Wettbewerber

---

## 3) Erste Tool-Idee: "FlightScope AI"

### Problemstellung
Kundenfeedback zu Airlines ist massiv, verstreut und schwer vergleichbar. 
Manager und Analysten brauchen schnelle, robuste, datenbasierte Wettbewerbsuebersichten.

Zusaetzlich reicht reine Review-Analyse fuer operative Netzwerkentscheidungen nicht aus. 
Fuer Fragen wie **"Sollen wir auf Strecke X im Monat Y mehr Fluege einsetzen?"** brauchen wir auch Preis- und Nachfrage-/Passagierdaten.

### Tool-Ziel
Ein LLM-gestuetztes Dashboard, das Airlines entlang zentraler Kundendimensionen vergleicht und Trends/Schwaechen frueh erkennt.

Erweitertes Ziel (Business Impact):
- Entscheidungshilfe fuer eine Airline, ob an einem Zeitpunkt auf einer Strecke
       - Frequenz erhoeht/reduziert werden soll,
       - ein groesseres/kleineres Flugzeug sinnvoll ist,
       - und welches Zeitfenster den besten Trade-off aus Nachfrage, Preis und Wettbewerb bietet.

### Geplanter Workflow
```text
[Input]
Auswahl von 4-8 Airlines + Strecke + Zeitraum + Datenquellen
       ->
[Data Collection]
Reviews/Kommentare + Preiszeitreihen + Nachfrage-/Passagierindikatoren sammeln
       ->
[Analysis Layer]
LLM: Aspekt-Extraktion, Sentiment, Evidenz-Zitate
Forecasting/OR: Nachfrageprognose + Kapazitaetsabgleich
       ->
[Visualization]
Radar, Ranking, Head-to-Head, Preis-/Nachfragetrend,
"Add/Hold/Reduce" + Flugzeuggroessen-/Zeitslot-Empfehlung
```

### Erste Analyse-Dimensionen (MVP)
1. **Puenktlichkeit & Zuverlaessigkeit**
2. **Preis & Gebuehrentransparenz**
3. **Kundenservice & Stoerungsmanagement**
4. **Digitale Experience (App/Web, Self-Service)**
5. **Bord- und Reiseerlebnis (Komfort/Gepaeck/Boarding)**
6. **Erstattungs- und Umbuchungsqualitaet**
7. **Preisniveau pro Strecke/Zeitslot**
8. **Nachfrage-/Passagierindikatoren pro Strecke/Zeitslot**

### MVP-Features fuer den Prototyp
- Radar-Chart fuer 4-8 Airlines
- Dimension-Ranking mit Evidenzzitaten aus Reviews
- Head-to-Head Vergleich zweier Airlines
- Monats-/Quartalstrend fuer Sentiment und kritische Themen
- Preis- und Nachfrage-Monitor je Pilotstrecke
- Regelbasierte Entscheidung: **Add / Hold / Reduce Flight**
- Grobe Aircraft-Size Empfehlung (Small/Medium/Large Narrowbody)

### Software-Umsetzung (dein Sprecherteil)
- **BYOK-Ansatz**: Nutzer geben im Tool einen eigenen API-Key ein (Google oder OpenRouter-kompatibel)
- **Fallback auf OpenRouter**: Wenn kein gueltiger Primar-Key verfuegbar ist, nutzen wir OpenRouter als Gateway
- **Engine-Unabhaengigkeit**: Gleiche Analysepipeline, austauschbares Modell-Backend
- **Sichere Demo-Strategie**: Team kann das Tool im Kurs auch dann stabil zeigen, wenn einzelne Keys ausfallen
- **Hybrid-Stack**: LLM fuer Text-Intelligence + Forecasting/Optimierung fuer Kapazitaetsentscheidung

### UI-Entwurf (fuer die Tool-Vorstellung)
- **Sidebar: API & Engine Settings**
       - Key-Eingabe
       - Provider-Auswahl (z. B. Google Direct / OpenRouter)
       - "Test Connection" Button
- **Analysebereich oben**
       - Airline-Auswahl (4-8 Anbieter)
       - Streckenwahl (Origin-Destination)
       - Zeitraum- und Quellenfilter
       - "Run Analysis" Button
- **Ergebnisbereich als Tabs**
       - Overview (KPI + Radar)
       - Rankings (je Dimension)
       - Head-to-Head (2 Anbieter im Detail)
       - Evidence (reprasentative Zitate als Beleg)
       - Capacity Planner (Add/Hold/Reduce, Aircraft Size, Time-Slot Vorschlag)

### Machbarkeit: Koennen wir das erreichen?
**Ja, in Stufen.**

Stufe 1 (kurzfristig, machbar fuer Kurs-Demo):
- Review + Preisdaten + einfache Nachfrageproxies integrieren
- Regelbasiertes Entscheidungssystem fuer Frequenz/Zeitslot/Aircraft-Size

Stufe 2 (mittelfristig):
- Zeitreihenprognose pro Strecke/Zeitslot
- Backtesting der Empfehlungen gegen historische Daten

Stufe 3 (spaeter, produktionsnah):
- Netzwerkweite Optimierung mit Flotten- und Slot-Constraints
- Szenarioanalyse (Fuel Cost, Seasonality, Wettbewerberreaktion)

---

## 4) Direkte Uebertragbarkeit aus dem StromCheck-Projekt

Was wir wiederverwenden koennen:
- **Pipeline-Logik**: Data Collection -> LLM-Scoring -> Dashboard
- **Darstellungslogik**: Radar, Ranking, Deep-Dive, Head-to-Head
- **Methodik**: dimensionsbasiertes Prompting + strukturierte JSON-Ausgabe
- **Technik-Stack**: Streamlit + LLM API (Google/OpenRouter) + Caching

Was wir anpassen muessen:
- Scraper-Quellen (Airline-Plattformen statt Energieanbieter-Plattformen)
- Dimensionsdefinition und Keywords auf Luftfahrtkontext
- Event-spezifische Labels (Delay, Cancellation, Rebooking, Baggage Issues)

---

## 5) Vorschlag fuer 10-Minuten-Praesentation

1. **0:00-1:00 | Motivation + Branchenwahl**
- Warum Luftfahrt? Warum jetzt? Warum geeignet fuer LLM-Analyse?

2. **1:00-3:30 | Literaturgrundlage**
- Porter -> Marktstruktur
- IPA/Kano -> Kundendimensionen priorisieren
- LLM-Cure -> methodischer Analysekern

3. **3:30-6:00 | Brancheneingrenzung und Wettbewerberauswahl**
- Scope (EU, Kurz-/Mittelstrecke)
- 6-7 Ziel-Airlines fuer die erste Iteration

4. **6:00-8:30 | Tool-Idee FlightScope AI**
- Workflow, MVP-Funktionen, Beispieloutput

5. **8:30-10:00 | Naechste Schritte**
- Datensammlung starten
- Prompt- und Dimensionsschema finalisieren
- Erste Demo mit 2 Airlines erstellen

---

## 6) Folienvorschlag (direkt in PPT uebernehmbar)

- **Folie 1**: Titel + Team + Forschungsfrage
- **Folie 2**: Warum Luftfahrt als Branche?
- **Folie 3**: Brancheneingrenzung (Scope, Segment, Anbieter)
- **Folie 4**: Literatur 1 (Porter) -> Nutzen fuer unser Projekt
- **Folie 5**: Literatur 2 (IPA/Kano) -> Nutzen fuer unser Projekt
- **Folie 6**: Literatur 3 (LLM-Cure) -> Nutzen fuer unser Projekt
- **Folie 7**: Erste Wettbewerbsdimensionen
- **Folie 8**: Tool-Konzept FlightScope AI (Workflow)
- **Folie 9**: MVP-Funktionen + erwarteter Mehrwert
- **Folie 10**: Arbeitsplan bis zur naechsten Session

---

## 7) Offene Punkte (fuer Team-Entscheidung)
- Soll "Flughaefen" explizit im Scope sein oder nur Airlines?
- Welche Sprache fuer Reviews zuerst: Deutsch oder Englisch oder beides?
- Erstes Demo-Set: 2 Airlines (z. B. Lufthansa vs Ryanair) oder direkt 4?

---

*Hinweis: Dieses Dokument ist als direkte Vorlage fuer die 10-min Gruppenpraesentation erstellt und orientiert sich methodisch am bestehenden StromCheck-Ansatz.*
