# README: Datenquellen_Template_FlightScope.xlsx

Dieses Dokument erklaert, wie das Excel-Template fuer die Datensammlung korrekt ausgefuellt wird.

Ziel: Einheitliche, vergleichbare und modellierbare Daten fuer FlightScope AI.

## Wichtige Arbeitsaufteilung (bitte zuerst lesen)

- Sie fuellen nur das Blatt `Datenquellen` aus.
- Fuer Sie gilt daher: pro Informationspunkt URLs + URL-spezifische Bewertung (Direkt/Proxy/Bias/Korrektur) + Zeitraum + kurze Bemerkung in `Datenquellen` eintragen, sonst nichts.

## 1) Datei und Arbeitsblaetter

Die Datei enthaelt vier Blaetter:

1. `Datenquellen`
- Hauptblatt fuer URL-Sammlung und Felddefinition je Informationspunkt.

2. `Hinweise`
- Kurzanleitung mit den wichtigsten Regeln.

3. `Bias_Check`
- Qualitaetsblatt zur Dokumentation von Verzerrungen (Bias) und Gegenmassnahmen.

4. `Feature_Catalog`
- Modellierungsblatt mit feineren Features, Datentypen, Ebenen und Bias-Behandlung.

## 2) Allgemeine Fuellregeln

1. Pro Zeile ein Informationspunkt
- Jede Zeile beschreibt einen Datentyp, z. B. Preisdaten oder Operative Qualitaet.

2. Mehrere Quellen eintragen
- Wenn moeglich mindestens 2 URLs pro Informationspunkt eintragen (`URL 1`, `URL 2`, ...).

3. Pro URL Qualitaet markieren
- Fuer jede eingetragene URL bitte auch ausfuellen:
	- `Direkt messbar URL X? (Ja/Nein/Teilweise)`
	- `Relevanz URL X (hoch/mittel/niedrig)`
	- `Proxy URL X` (nur wenn nicht direkt messbar)
	- `Bias/Risiko URL X`
	- `Korrektur URL X`

4. Zeitraum immer angeben
- In `Abgedeckter Zeitraum` immer explizit schreiben, z. B. `2024-01 bis 2026-04`.

5. Zeilenebene als Zusammenfassung nutzen
- `Proxy-Definition (Zeilenebene)`, `Bias-/Risiko-Hinweis (Zeilenebene)` und `Empfohlene Korrektur (Zeilenebene)` sind Zusammenfassungen ueber alle URLs der Zeile.

### Wichtiger Zusatz: Was bedeuten die 3 Zeilenebene-Felder genau?

1. `Proxy-Definition (Zeilenebene)`
- Bedeutung: Welche Stellvertreter-Logik verwenden wir insgesamt fuer diesen Informationspunkt, wenn Daten nicht direkt beobachtbar sind?
- Warum ausfuellen: Damit spaeter im Modell klar ist, welche Groesse tatsaechlich gelernt/optimiert wird und wie sie berechnet wurde.
- Wie ausfuellen:
	- Kurz und formal, moeglichst als Formel oder eindeutige Regel.
	- Eine gemeinsame Definition fuer die ganze Zeile, nicht fuer einzelne URLs.
- Formatbeispiel:
	- `Estimated_Pax = Seats_total * predicted_LF`
	- `TotalTripCost_Proxy = Fare + BaggageFee + SeatFee (wenn verfuegbar)`

2. `Bias-/Risiko-Hinweis (Zeilenebene)`
- Bedeutung: Das wichtigste methodische Risiko ueber alle Quellen dieser Zeile.
- Warum ausfuellen: Damit Team und Kunden wissen, wo die Aussagegrenzen liegen (Transparenz statt Black Box).
- Wie ausfuellen:
	- 1 klare Hauptaussage (kein langer Absatz).
	- Nur das groesste Risiko nennen, nicht alle Details.
- Formatbeispiel:
	- `Posted fares weichen von Transaction fares ab.`
	- `Review-Daten haben Selection Bias (extreme Meinungen uebergewichtet).`

3. `Empfohlene Korrektur (Zeilenebene)`
- Bedeutung: Die wichtigste Gegenmassnahme gegen das oben genannte Risiko.
- Warum ausfuellen: Ohne Korrektur bleibt das Risiko nur dokumentiert, aber nicht behandelt.
- Wie ausfuellen:
	- 1-2 konkrete, umsetzbare Schritte.
	- Muss direkt zum Bias-Hinweis passen.
- Formatbeispiel:
	- `D-60/D-30/D-14/D-7 Snapshots und Plattform-Median verwenden.`
	- `Reweighting + Plattform Fixed Effects + Duplikatfilter.`

4. Kurzregel fuer Konsistenz
- Die drei Felder muessen logisch zusammenpassen:
	- Proxy sagt: Was messen wir?
	- Bias sagt: Wo ist das Hauptproblem?
	- Korrektur sagt: Wie reduzieren wir genau dieses Problem?

5. Haeufige Fehler (bitte vermeiden)
- Proxy leer lassen, obwohl URLs nur indirekte Daten liefern.
- Im Bias-Feld mehrere unsortierte Risiken auflisten.
- Korrektur eintragen, die nicht zum genannten Bias passt.
- URL-Ebene und Zeilenebene widersprechen sich.

6. Bias nicht leer lassen
- In `Bias-/Risiko-Hinweis` das Hauptproblem benennen.
- In `Empfohlene Korrektur` die konkrete Korrektur notieren.

7. Prioritaet setzen
- `MVP`: Muss frueh gesammelt werden.
- `P2`: Wichtig nach MVP.
- `P3`: Spaeter/optional.
- Hinweis: `Prioritaet` bleibt absichtlich auf Zeilenebene (Informationspunkt), nicht pro URL.

## 2b) API-First Regel (verbindlich)

Nur Quellen eintragen, die per Skript abrufbar sind (API oder strukturierter Download).

Empfohlene Startquellen (maschinenlesbar):

1. OpenSky REST API
- `https://opensky-network.org/apidoc/rest.html`

2. Eurostat Statistics API
- `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/`

3. Amadeus Self-Service APIs
- `https://developers.amadeus.com/`

4. Aviationstack API
- `https://aviationstack.com/documentation`

5. AirLabs API
- `https://airlabs.co/docs`

Nicht als Primaerquelle eintragen (nur manuelle UI, kein stabiler Vollabruf):
- `https://www.google.com/travel/flights`
- `https://www.skyscanner.com/`
- `https://www.kayak.com/flights`

Hinweis:
- Falls ein Anbieter nur aktuelle Quotes liefert (keine Historie), ist das zulaessig.
- Dann Historie ueber regelmaessige Polling-Snapshots selbst aufbauen (z. B. taeglich/stuendlich).

## 3) Spalten erklaert (Blatt: Datenquellen)

1. `Modul`
- Grobe Kategorie, z. B. `Preisdaten`, `Nachfrage-Proxies`.

2. `Informationspunkt`
- Konkreter Datentyp innerhalb des Moduls.

3. `Pflichtfelder (mindestens)`
- Felder, die zwingend vorhanden sein muessen.

4. `URL 1` bis `URL 4`
- Webseiten mit den benoetigten Daten.

5. `Direkt messbar URL 1..4? (Ja/Nein/Teilweise)`
- Pro URL separat markieren, ob die benoetigte Information direkt auslesbar ist.

6. `Relevanz URL 1..4 (hoch/mittel/niedrig)`
- Pro URL separat einschaetzen, wie nuetzlich die Quelle fuer den Informationspunkt ist.

7. `Proxy URL 1..4`
- URL-spezifische Proxy-Definition (falls die Quelle nicht direkt messbar ist).

8. `Bias/Risiko URL 1..4`
- URL-spezifisches Hauptrisiko.

9. `Korrektur URL 1..4`
- URL-spezifische Gegenmassnahme.

10. `Abgedeckter Zeitraum`
- Zeitabdeckung der Quelle.

11. `Proxy-Definition (Zeilenebene)`
- Zusammenfassende Proxy-Logik auf Informationspunkt-Ebene.

12. `Bias-/Risiko-Hinweis (Zeilenebene)`
- Zusammenfassende Risikoaussage auf Informationspunkt-Ebene.

13. `Empfohlene Korrektur (Zeilenebene)`
- Zusammenfassende Korrektur auf Informationspunkt-Ebene.

14. `Prioritaet (MVP/P2/P3)`
- Um Reihenfolge fuer das Team festzulegen.

15. `Bemerkungen`
- Freitext fuer technische Hinweise.

## 4) Spalten erklaert (Blatt: Feature_Catalog)

1. `Feature_Name`
- Eindeutiger technischer Name, z. B. `price_gap_vs_comp`.

2. `Typ`
- Datentyp, z. B. `numeric`, `binary`, `text-derived`.

3. `Ebene`
- Granularitaet, z. B. `route-week`, `route-date`, `review`, `airline-route-month`.

4. `Definition`
- Kurze fachliche Definition des Features.

5. `Quelle (Beispiel)`
- Beispielquelle oder Ableitungspfad.

6. `Direkt/Proxy`
- Ob das Feature direkt messbar oder ein Proxy ist.

7. `Bias-Risiko`
- Einfache Einstufung: `niedrig`, `mittel`, `hoch`.

8. `Empfohlene Behandlung`
- Konkrete Korrektur oder Robustheitsmassnahme.

9. `Prioritaet`
- `MVP`, `P2`, `P3`.

## 5) Beispiel (so sollte eine Zeile aussehen)

- Modul: `Preisdaten`
- Informationspunkt: `Preisniveau je Strecke/Zeitslot`
- Pflichtfelder: `Crawling-Datum, Abflugdatum, Airline, Strecke, Mindestpreis/Medianpreis`
- URL 1: `https://...`
- Direkt messbar URL 1: `Ja`
- Relevanz URL 1: `hoch`
- Proxy URL 1: leer
- Bias URL 1: `niedrig`
- Korrektur URL 1: leer
- URL 2: `https://...`
- Direkt messbar URL 2: `Teilweise`
- Relevanz URL 2: `mittel`
- Proxy URL 2: `Median aus mehreren Suchabfragen`
- Bias URL 2: `Posted fare != transaction fare`
- Korrektur URL 2: `D-60/D-30/D-14/D-7 Snapshots`
- Zeitraum: `2025-01 bis 2026-04`
- Proxy-Definition (Zeilenebene): `Preisproxy ueber mehrere Buchungsvorlaeufe`
- Bias-/Risiko-Hinweis (Zeilenebene): `Preisbeobachtung kann verzerrt sein`
- Empfohlene Korrektur (Zeilenebene): `Mehrere Plattformen + Zeitfenster`
- Prioritaet: `MVP`
- Bemerkungen: `Preis inkl./exkl. Gepaeck klar markieren`

## 6) Hinweise fuer Textdaten (Reviews)

1. Immer Plattform mit speichern
- Beispiel: Trustpilot, App Store, Google Reviews.

2. Sprache mit speichern
- z. B. `de`, `en`.

3. Bias beachten
- Reviews sind oft ueberproportional positiv oder negativ.
- Nicht als alleinige Zielvariable verwenden, sondern als Feature.

## 7) Definition fuer unser Zielkonstrukt

Falls reale Ticketverkaeufe nicht verfuegbar sind, nutzen wir:

- `Estimated_Pax = Seats_total * predicted_LF`

Dabei gilt:
- `Seats_total`: aus Flugplan + Flugzeugtyp
- `predicted_LF`: datengetriebene Schaetzung (nicht manuell geraten)

## 8) Mini-Checkliste vor Abgabe

1. Sind pro MVP-Zeile mindestens 2 URLs vorhanden?
2. Sind fuer jede eingetragene URL die Felder `Direkt messbar`, `Relevanz`, `Proxy`, `Bias`, `Korrektur` gepflegt?
3. Ist der Zeitraum fuer jede Zeile gefuellt?
4. Ist die Zeilenebene-Summary (`Proxy/Bias/Korrektur`) konsistent mit den URL-Eintraegen?
5. Ist eine Prioritaet (`MVP/P2/P3`) gesetzt?

Zusatz fuer Kernteam:
6. Sind Zeilen mit hoher Prioritaet (`MVP`) vollstaendig vor `P2/P3` gepflegt?
7. Ist fuer neue modellrelevante Punkte ein Eintrag in `Feature_Catalog` vorhanden?
8. Sind Proxy-Features im Blatt `Bias_Check` mit passender Korrekturlogik abgedeckt?
9. Sind in `URL 1..4` nur API/Download-Quellen und keine UI-only Seiten eingetragen?

Wenn alle 9 Punkte erfuellt sind, ist die Zeile bereit fuer Modellierung.

## 9) Quickstart fuer automatisches Sammeln (ohne manuelles Klicken)

1. API Keys setzen
- Datei `collector_env.example` als Vorlage nutzen und Werte in Umgebungsvariablen setzen.

2. Einmaliger Testlauf
- `python collect_sources.py --loop-seconds 0`

3. Dauerbetrieb (Snapshot-Polling)
- `python collect_sources.py --loop-seconds 3600`

4. Ausgabeorte
- Rohdaten werden unter `data/raw/<source>/timestamp.json` gespeichert.

5. Wichtiger Hinweis
- Preis-Historie ist meist nicht direkt verfuegbar. Historie entsteht durch eigene regelmaessige Snapshots.
