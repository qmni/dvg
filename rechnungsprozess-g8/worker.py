import asyncio
import logging
from pyzeebe import ZeebeWorker, create_insecure_channel

# Logging zeigt dir Fehler direkt in der Konsole an
logging.basicConfig(level=logging.INFO)

# VERBINDUNG ZUM LOKALEN CLUSTER
# Port 26500 ist der Standard-Port für die Zeebe-Engine in Docker
channel = create_insecure_channel(hostname="localhost", port=26500)
worker = ZeebeWorker(channel)

# --- DEINE PROZESS-SCHRITTE (SERVICE TASKS) ---

@worker.task(task_type="metadaten-extrahieren")
async def task_extraction():
    print("\n[INFO] Schritt: Metadaten extrahieren...")
    return {"extraktionErfolgreich": True}

@worker.task(task_type="pflichtdaten-prüfen")
async def task_check_data():
    print("[INFO] Schritt: Pflichtdaten prüfen...")
    return {"pflichtdatenVorhanden": True}

@worker.task(task_type="rechnungsdaten-validieren")
async def task_validation():
    print("[INFO] Schritt: Daten validieren...")
    # Wir setzen dies auf False, damit wir direkt zum ERP-System springen
    return {"complianceCheckNotwendig": False}

@worker.task(task_type="erp-system")
async def task_erp():
    print("[INFO] Schritt: Übertragung ins ERP-System...")
    return {"manuelleFreigabeNoetig": False}

@worker.task(task_type="payment-service")
async def task_payment():
    print("[INFO] Schritt: Payment Service aufgerufen...")
    return {}

@worker.task(task_type="zahlung-ausführen")
async def task_final():
    print("[INFO] Schritt: Zahlung wurde final ausgeführt!")
    return {}

async def main():
    print("--- LOKALER WORKER GESTARTET ---")
    print("Verbindung zu localhost:26500 wird aufgebaut...")
    await worker.work()

if __name__ == "__main__":
    asyncio.run(main())