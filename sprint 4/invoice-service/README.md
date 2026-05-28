# sprint-4

## Setup

```bash
# 1. Virtuelle Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# 2. Abhängigkeiten installieren
pip install -r validation-compliance-services/requirements.txt
```

## Run

### Als FastAPI-Server (empfohlen)

```bash
# Im Projektordner sprint-4
.venv/bin/python -m uvicorn main:app --reload --app-dir validation-compliance-services
```

Server läuft auf: http://127.0.0.1:8000

API-Dokumentation: http://127.0.0.1:8000/docs

### Direkt als Skript

```bash
.venv/bin/python validation-compliance-services/main.py
```

## Endpunkte

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| POST | `/check-invoice` | Rechnung validieren und auf Compliance prüfen |