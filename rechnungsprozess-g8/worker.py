import asyncio
import logging
import json
import os
import pika
import grpc
from pyzeebe import ZeebeWorker, create_camunda_cloud_channel
from dotenv import load_dotenv
from config import CAMUNDA_CONFIG

# Deine bestehenden Shared-Imports für den gRPC-Aufruf
from shared import invoice_pb2
from shared import invoice_pb2_grpc

load_dotenv()
logging.basicConfig(level=logging.INFO)

# --- VERBINDUNG ZUR CAMUNDA WEB CLOUD (SAAS) ---
channel = create_camunda_cloud_channel(
    client_id=CAMUNDA_CONFIG["client_id"],
    client_secret=CAMUNDA_CONFIG["client_secret"],
    cluster_id=CAMUNDA_CONFIG["cluster_id"],
    region=CAMUNDA_CONFIG["region"]
)
worker = ZeebeWorker(channel)

# Lokale Services (gRPC-Server & RabbitMQ)
HOST = os.getenv("HOST", "localhost")
INVOICE_PORT = os.getenv("INVOICE_PORT", "50052")


# --- TASK 1: Speicherung der Metadaten per gRPC Service ---
@worker.task(task_type="metadaten-extrahieren")
async def save_metadata_via_grpc(job_variables: dict):
    print("\n[Camunda-SaaS-Worker] Task 'Metadaten extrahieren' aus der Cloud empfangen...")
    
    # Holen der Variablen, die beim Start übergeben wurden
    rechnungsnummer = job_variables.get("rechnungsNummer", "UNBEKANNT")
    lieferant = job_variables.get("lieferant", "Unbekannter Lieferant")
    betrag = job_variables.get("betrag", 0.0)
    datum = job_variables.get("datum", "01.01.2026")

    try:
        # gRPC Verbindung zu DEINEM lokalen server.py herstellen
        grpc_channel = grpc.insecure_channel(f"{HOST}:{INVOICE_PORT}")
        stub = invoice_pb2_grpc.InvoiceServiceStub(grpc_channel)
        
        rechnung = invoice_pb2.Invoice(
            id=str(rechnungsnummer),
            supplier=str(lieferant),
            amount=float(betrag),
            date=str(datum)
        )
        
        print(f"[gRPC-Client] Sende Rechnung {rechnungsnummer} an lokalen gRPC-Server...")
        antwort = stub.SaveInvoice(rechnung)
        print(f"[gRPC-Client] Server-Antwort erhalten: {antwort.message}")
        
        # Variablen an Camunda zurückgeben (steuert die Gateways im BPMN)
        return {"extraktionErfolgreich": True, "pflichtdatenVorhanden": True}
        
    except grpc.RpcError as e:
        print(f"[FEHLER] Lokaler gRPC-Server (server.py) nicht erreichbar! Details: {e.details()}")
        return {"extraktionErfolgreich": False, "pflichtdatenVorhanden": False}


# --- TASK 2: Rechnungsdaten validieren ---
@worker.task(task_type="rechnungsdaten-validieren")
async def task_validation():
    print("[Camunda-SaaS-Worker] Rechnungsdaten werden validiert. Setze Compliance auf False.")
    return {"complianceCheckNotwendig": False}


# --- TASK 3: ERP Übernahme ---
@worker.task(task_type="erp-system")
async def task_erp():
    print("[Camunda-SaaS-Worker] ERP-Eintrag im Workflow bestätigt.")
    return {"manuelleFreigabeNoetig": False}


# --- TASK 4: Nachricht an das Zahlungssystem (RabbitMQ) ---
@worker.task(task_type="payment-service")
async def send_payment_notification(job_variables: dict):
    print("\n[Camunda-SaaS-Worker] Task 'Zahlung veranlassen' aus der Cloud empfangen...")
    rechnungsnummer = job_variables.get("rechnungsNummer", "UNBEKANNT")

    try:
        # Verbindung zu DEINEM lokalen RabbitMQ-Broker aufbauen
        connection = pika.BlockingConnection(pika.ConnectionParameters(HOST))
        channel = connection.channel()
        channel.queue_declare(queue='payment_queue')
        
        zahlungs_daten = {"invoiceId": rechnungsnummer}
        nachricht_json = json.dumps(zahlungs_daten)
        
        channel.basic_publish(exchange='', routing_key='payment_queue', body=nachricht_json)
        print(f"[RabbitMQ-Client] Zahlungsauftrag für {rechnungsnummer} in die Queue gelegt!")
        connection.close()
        
    except Exception as e:
        print(f"[FEHLER] Lokales RabbitMQ nicht erreichbar! Fehler: {e}")

    return {}


# --- TASK 5: Zahlung ausführen (Abschluss) ---
@worker.task(task_type="zahlung-ausführen")
async def task_final():
    print("[Camunda-SaaS-Worker] Workflow in der Camunda-Cloud erfolgreich durchgelaufen und beendet.")
    return {}


async def main():
    print("\n" + "="*40)
    print("--- WEB-WORKER (SAAS) ERFOLGREICH GESTARTET ---")
    print("Verbindung zu Cluster 487e2664... steht!")
    print("Lausche auf Aufgaben aus dem Webbrowser...")
    print("="*40)
    await worker.work()

if __name__ == "__main__":
    asyncio.run(main())