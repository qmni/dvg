# Sprint 5 – UiPath RPA Bot

Dieser Ordner enthält den UiPath-Bot für Sprint 5.

## Was macht der Bot?

Der Bot automatisiert die Eingabe von Rechnungsdaten in das ERP-Frontend.

Ablauf:

1. ERP-Webseite öffnen
2. Rechnungsdaten eintragen
3. Einen Beispiel-Rechnungsposten eintragen
4. Rechnung speichern

## Eingabedaten

Der Bot hat vier Input-Werte, die theoretisch von außen übergeben werden können, z. B. aus Camunda:

- `id`
- `supplier`
- `amount`
- `date`

Diese Inputs haben Default-Werte, damit der Bot auch direkt in UiPath Studio getestet werden kann.

## Weitere verwendete Daten

Zusätzlich verwendet der Bot interne Variablen für die ERP-Erfassung, z. B.:

- Rechnungsnummer
- Lieferantenname
- Rechnungsdatum
- Kundennummer
- Zahlungsziel
- Bemerkung
- Beschreibung
- Stückzahl
- Einheit

Damit wird im ERP-System eine Beispielrechnung mit einem Rechnungsposten erstellt.