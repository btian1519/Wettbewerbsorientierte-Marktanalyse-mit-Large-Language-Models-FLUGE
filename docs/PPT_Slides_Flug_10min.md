# PPT Slides Draft (10 Min) — Flight Market LLM Analysis

## Slide 1 — Titel
**FlightScope AI**  
Wettbewerbsorientierte Marktanalyse im europaeischen Flugmarkt mit LLMs  
Team: [Name 1], [Name 2], [Name 3]

---

## Slide 2 — Problem und Motivation
- Airline-Wettbewerb ist stark, Kundenfeedback ist riesig aber unstrukturiert
- Manuelle Konkurrenzanalyse ist langsam und subjektiv
- LLMs koennen grosse Reviewmengen in strukturierte Insights umwandeln
- Fuer operative Entscheidungen fehlen oft integrierte Daten zu **Preisniveau** und **Nachfrage/Passagieraufkommen**

---

## Slide 3 — Branche eingrenzen
- Fokus: Passagierflugverkehr in Europa (Kurz-/Mittelstrecke)
- Vergleichstypen:
  - Network: Lufthansa, Air France, KLM
  - Low-Cost: Ryanair, easyJet, Wizz Air
- Datenperspektive: deutschsprachige und internationale Reviews

---

## Slide 4 — Literaturgrundlage 1 (Porter)
- Five Forces als Struktur fuer Marktverstaendnis
- Relevanz fuer Luftfahrt:
  - Hohe Rivalitaet
  - Hohe Preistransparenz fuer Kunden
  - Hohe Eintrittsbarrieren (Slots, Flotte, Regulierung)

---

## Slide 5 — Literaturgrundlage 2 (IPA + Kano)
- Kundenerwartungen in Basis-, Leistungs- und Begeisterungsfaktoren trennen
- Uebertragung auf Airlines:
  - Basis: Sicherheit, Zuverlaessigkeit
  - Leistung: Puenktlichkeit, Preis-Leistung
  - Begeisterung: kulante Umbuchung, exzellente App

---

## Slide 6 — Literaturgrundlage 3 (LLM-Cure)
- LLMs extrahieren Staerken/Schwaechen aus Reviews
- Standardisiertes Scoring ueber mehrere Wettbewerber
- Direkte methodische Vorlage fuer unser Tool

---

## Slide 7 — Erste Wettbewerbsdimensionen
1. Puenktlichkeit und Zuverlaessigkeit
2. Preis und Gebuehrentransparenz
3. Kundenservice und Stoerungsmanagement
4. Digitale Experience (App/Web)
5. Bord- und Reiseerlebnis
6. Erstattungs- und Umbuchungsqualitaet

Erweiterung fuer Entscheidungsunterstuetzung (neu):
7. Preisniveau pro Strecke/Zeitslot (Ticketpreise, Preiselastizitaet)
8. Nachfrageindikatoren (Passagieraufkommen, Auslastungsproxy, Such-/Buchungstrends)

---

## Slide 8 — Tool-Idee: FlightScope AI
Workflow:
1. Airlines + Strecke + Zeitraum + Quellen waehlen
2. Multi-Source Daten sammeln: Reviews + Preiszeitreihen + Nachfrage/Passagierproxies
3. LLM + Forecasting analysieren Dimensionen, Nachfrage und Wettbewerbssituation
4. Dashboard zeigt Radar, Ranking, Head-to-Head, Nachfrage- und Preis-Trends

Software-Architektur (fuer deinen Part):
- **BYOK (Bring Your Own Key)**: Nutzer geben im UI ihren eigenen API-Key ein
- **Fallback-Logik**: Wenn kein gueltiger Key vorhanden ist, kann OpenRouter als Standard-Gateway genutzt werden
- **Vorteil**: Hohe Flexibilitaet, geringere Abhaengigkeit von einem einzelnen Modellanbieter, leichter Demo-Betrieb im Kurs

Was bedeutet der End-to-End-Flow konkret?
- **Input**: Wir definieren, *wen* wir vergleichen (z. B. Lufthansa vs Ryanair), *welchen Zeitraum* und *welche Quellen*
- **Datensammlung**: Tool sammelt Rohtexte aus Reviews/App-Bewertungen, Ticketpreis-Snapshots und Nachfrage-/Passagierindikatoren
- **Analyse-Ebene 1 (LLM)**: Modell strukturiert freie Texte in vergleichbare Kategorien (Scores, Sentiment, Belegzitate)
- **Analyse-Ebene 2 (Forecasting/OR)**: Nachfrageprognose + Kapazitaetsabgleich je Strecke und Zeitslot
- **Visualisierung**: Ergebnisse werden fuer Entscheidungen sichtbar gemacht (Radar, Ranking, Trend, Kapazitaetsluecken)

UI-Konzept (zusaetzlich):
- **Sidebar "API & Engine"**: Key-Eingabe, Provider-Wahl (Google/OpenRouter), Connection-Test
- **Control Panel**: Airline-Auswahl, Strecke, Zeitraum, Quellenfilter, "Run Analysis"
- **Result Tabs**:
  - Overview: KPI-Karten + Radar
  - Dimension Ranking: Vergleich je Kriterium
  - Head-to-Head: 2-Airline-Detailvergleich
  - Evidence View: Zitate/Problemmuster als Nachweis
  - Capacity Planner: Empfehlung zu Frequenz, Flugzeuggroesse und Abflugzeitfenster

---

## Slide 9 — MVP und Nutzen
MVP:
- Radarvergleich fuer 4-8 Airlines
- Evidenzbasierte Rankings pro Dimension
- Head-to-Head Analyse zweier Airlines
- Zeittrend kritischer Themen
- Preis- und Nachfragemonitor je Strecke (Pilot)
- Erste regelbasierte Kapazitaetsempfehlung: *Add / Hold / Reduce Flight*

MVP bedeutet hier (einfach erklaert):
- **Nicht** die perfekte Endversion
- **Sondern** die kleinste funktionsfaehige Version, die den Kernnutzen zeigt
- Konkret: schon mit 2-4 Airlines valide Vergleichsinsights liefern, auch wenn spaetere Features noch fehlen

Nutzen:
- Schnellere, datenbasierte Wettbewerbsentscheidungen
- Frueherkennung von Serviceproblemen und Differenzierungspotenzial
- Operative Entscheidungshilfe: **Soll eine Airline zu Zeitpunkt t auf Strecke r Frequenz erhoehen?**
- Taktische Empfehlung: **Welche Flugzeuggroesse (z. B. A320neo vs A321neo) und welches Zeitfenster?**

---

## Slide 10 — Next Steps
- Scope finalisieren (Airlines only vs. Airlines + Airports)
- Erste Datensammlung fuer 2 Airlines + 2 Strecken (Pilot)
- Prompt- und Dimensionsschema validieren
- Entscheidungslogik fuer Add/Hold/Reduce und Aircraft-Size Regeln implementieren
- Erste klickbare Demo bis zur naechsten Session

---

## Backup Slide A — Capacity Planner Logik (Input -> Rule Engine -> Output)

Ziel:
- Entscheidung fuer Strecke r zum Zeitpunkt t: **Add / Hold / Reduce**
- Empfehlung fuer **Aircraft Size** und **Time Slot**

Input Features:
- Preisniveau und Preisveraenderung je Strecke/Slot
- Nachfrageproxy (Search Trend, Buchungsproxy, Review-Volumen)
- Angebotsseite (aktuelle Frequenz, Seats per Week, Wettbewerberkapazitaet)
- Operative Qualitaet (OTP, Cancellation Rate, Service Stress aus Reviews)
- Kalenderfaktoren (Wochentag, Feiertage, Saison)

Rule Engine (MVP, transparent):
- Schritt 1: Demand Pressure Score berechnen
- Schritt 2: Supply Gap Score berechnen
- Schritt 3: Profitability Proxy berechnen
- Schritt 4: Risikoabschlag fuer schlechte Operations-Qualitaet
- Schritt 5: Final Score -> Entscheidung ableiten

Einfaches Entscheidungsprinzip:
- Wenn Demand hoch + Supply Gap positiv + Risiko ok -> **Add Flight**
- Wenn Scores stabil im Mittelfeld -> **Hold**
- Wenn Demand schwach oder Risiko hoch -> **Reduce / no expansion**

Aircraft-Size Heuristik (MVP):
- Add Flight + mittlere Nachfrage -> Small Narrowbody
- Add Flight + hohe Nachfrage + Peak Slot -> Medium/Large Narrowbody
- Hohe Unsicherheit -> erst Frequenz testen, dann Upsizing

Time-Slot Empfehlung:
- Peak-Slots priorisieren, wenn Nachfrage robust und OTP stabil
- Off-Peak nutzen, wenn Preiselastizitaet hoch und Slotkosten geringer

Output im UI (Capacity Planner Tab):
- Entscheidungskarte je Strecke: Add / Hold / Reduce
- Empfohlene Flugzeugklasse und Zeitfenster
- Top-3 Begruendungen (datenbasiert) + Confidence Score
