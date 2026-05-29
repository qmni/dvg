import asyncio
import logging
import json
import os
import sys
from pathlib import Path

import grpc
import pika
from dotenv import load_dotenv
from pyzeebe import ZeebeWorker, create_camunda_cloud_channel


# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Pfad zu "sprint 1" hinzufügen, damit invoice_pb2 importiert werden kann
SPRINT_1_PATH = Path(__file__).resolve().parents[1] / "sprint 1"
sys.path.append(str(SPRINT_1_PATH))

import invoice_pb2
import invoice_pb2_grpc


INVOICE_HOST = os.getenv("INVOICE_HOST", "localhost")
INVOICE_PORT = os.getenv("INVOICE_PORT", "50052")

# Für RabbitMQ; falls ihr keinen separaten Wert habt, wird localhost genutzt
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")


# ------------------------------------------------------------
# Camunda Cloud Verbindung
# ------------------------------------------------------------

channel = create_camunda_cloud_channel()
worker = ZeebeWorker(channel)


# ------------------------------------------------------------
# TASK: Rechnung ins Invoice Service speichern
# BPMN Task Type: save-invoice
# ------------------------------------------------------------

@worker.task(task_type="save-invoice")
async def save_invoice(job_variables: dict):
    print("\n[Camunda-Worker] Task 'save-invoice' empfangen.")
    print("[DEBUG] Empfangene Variablen:", job_variables)

    rechnungsnummer = job_variables.get("rechnungsNummer")
    lieferant = job_variables.get("lieferant")
    betrag = job_variables.get("betrag")
    datum = job_variables.get("datum")

    if not rechnungsnummer or not lieferant or betrag is None or not datum:
        fehlermeldung = "Pflichtdaten fehlen: rechnungsNummer, lieferant, betrag oder datum"
        print(f"[FEHLER] {fehlermeldung}")

        return {
            "invoice_saved": False,
            "invoice_error": fehlermeldung
        }

    try:
        grpc_channel = grpc.insecure_channel(f"{INVOICE_HOST}:{INVOICE_PORT}")
        stub = invoice_pb2_grpc.InvoiceServiceStub(grpc_channel)

        rechnung = invoice_pb2.Invoice(
            id=str(rechnungsnummer),
            supplier=str(lieferant),
            amount=float(betrag),
            date=str(datum)
        )

        print(f"[gRPC] Sende Rechnung {rechnungsnummer} an {INVOICE_HOST}:{INVOICE_PORT} ...")
        antwort = stub.SaveInvoice(rechnung)
        print(f"[gRPC] Antwort vom Invoice Service: {antwort.message}")

        return {
            "invoice_saved": True,
            "invoice_message": antwort.message
        }

    except ValueError:
        fehlermeldung = f"Betrag ist keine gültige Zahl: {betrag}"
        print(f"[FEHLER] {fehlermeldung}")

        return {
            "invoice_saved": False,
            "invoice_error": fehlermeldung
        }

    except grpc.RpcError as e:
        fehlermeldung = e.details()
        print(f"[FEHLER] gRPC-Fehler: {fehlermeldung}")

        return {
            "invoice_saved": False,
            "invoice_error": fehlermeldung
        }

    except Exception as e:
        fehlermeldung = str(e)
        print(f"[FEHLER] Unerwarteter Fehler: {fehlermeldung}")

        return {
            "invoice_saved": False,
            "invoice_error": fehlermeldung
        }


# ------------------------------------------------------------
# TASK: Rechnungsdaten validieren
# BPMN Task Type: rechnungsdaten-validieren
# ------------------------------------------------------------

@worker.task(task_type="rechnungsdaten-validieren")
async def task_validation():
    print("[Camunda-Worker] Task 'rechnungsdaten-validieren' empfangen.")

    return {
        "complianceCheckNotwendig": False
    }


# ------------------------------------------------------------
# TASK: ERP-System
# BPMN Task Type: erp-system
# ------------------------------------------------------------

@worker.task(task_type="erp-system")
async def task_erp():
    print("[Camunda-Worker] Task 'erp-system' empfangen.")

    return {
        "manuelleFreigabeNoetig": False,
        "erp_erfolgreich": True
    }


# ------------------------------------------------------------
# TASK: Zahlungsauftrag an Payment Service senden
# BPMN Task Type: payment-service
# ------------------------------------------------------------

@worker.task(task_type="payment-service")
async def send_payment_notification(job_variables: dict):
    print("\n[Camunda-Worker] Task 'payment-service' empfangen.")
    print("[DEBUG] Empfangene Variablen:", job_variables)

    rechnungsnummer = job_variables.get("rechnungsNummer", "UNBEKANNT")

    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        rabbit_channel = connection.channel()
        rabbit_channel.queue_declare(queue="payment_queue")

        zahlungs_daten = {
            "invoiceId": rechnungsnummer
        }

        nachricht_json = json.dumps(zahlungs_daten)

        rabbit_channel.basic_publish(
            exchange="",
            routing_key="payment_queue",
            body=nachricht_json
        )

        print(f"[RabbitMQ] Zahlungsauftrag für Rechnung {rechnungsnummer} gesendet.")
        connection.close()

        return {
            "payment_message_sent": True
        }

    except Exception as e:
        fehlermeldung = str(e)
        print(f"[FEHLER] RabbitMQ nicht erreichbar: {fehlermeldung}")

        return {
            "payment_message_sent": False,
            "payment_error": fehlermeldung
        }


# ------------------------------------------------------------
# TASK: Zahlung ausführen
# BPMN Task Type: zahlung-ausführen
# ------------------------------------------------------------

@worker.task(task_type="zahlung-ausführen")
async def task_final():
    print("[Camunda-Worker] Task 'zahlung-ausführen' empfangen.")
    print("[Camunda-Worker] Workflow abgeschlossen.")

    return {}


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

async def main():
    print("\n" + "=" * 50)
    print("--- CAMUNDA WORKER GESTARTET ---")
    print(f"Invoice gRPC Server: {INVOICE_HOST}:{INVOICE_PORT}")
    print(f"RabbitMQ Host: {RABBITMQ_HOST}")
    print("Lausche auf Tasks aus Camunda Cloud...")
    print("=" * 50)

    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())