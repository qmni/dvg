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

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)

# Pfad zu "sprint 1" hinzufügen, damit invoice_pb2 importiert werden kann
SPRINT_1_PATH = Path(__file__).resolve().parents[1] / "sprint 1"
sys.path.append(str(SPRINT_1_PATH))

import invoice_pb2
import invoice_pb2_grpc


# ------------------------------------------------------------
# Umgebungsvariablen
# ------------------------------------------------------------

INVOICE_HOST = os.getenv("INVOICE_HOST", "localhost")
INVOICE_PORT = os.getenv("INVOICE_PORT", "50052")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

ZEEBE_CLIENT_ID = os.getenv("ZEEBE_CLIENT_ID") or os.getenv("CAMUNDA_CLIENT_ID")
ZEEBE_CLIENT_SECRET = os.getenv("ZEEBE_CLIENT_SECRET") or os.getenv("CAMUNDA_CLIENT_SECRET")
ZEEBE_CLUSTER_ID = os.getenv("ZEEBE_CLUSTER_ID") or os.getenv("CAMUNDA_CLUSTER_ID")
ZEEBE_REGION = os.getenv("ZEEBE_REGION") or os.getenv("CAMUNDA_REGION")

# pyzeebe erwartet je nach Version CAMUNDA_* oder ZEEBE_*.
# Deshalb setzen wir beide Varianten explizit.
if ZEEBE_CLIENT_ID:
    os.environ["ZEEBE_CLIENT_ID"] = ZEEBE_CLIENT_ID
    os.environ["CAMUNDA_CLIENT_ID"] = ZEEBE_CLIENT_ID

if ZEEBE_CLIENT_SECRET:
    os.environ["ZEEBE_CLIENT_SECRET"] = ZEEBE_CLIENT_SECRET
    os.environ["CAMUNDA_CLIENT_SECRET"] = ZEEBE_CLIENT_SECRET

if ZEEBE_CLUSTER_ID:
    os.environ["ZEEBE_CLUSTER_ID"] = ZEEBE_CLUSTER_ID
    os.environ["CAMUNDA_CLUSTER_ID"] = ZEEBE_CLUSTER_ID

if ZEEBE_REGION:
    os.environ["ZEEBE_REGION"] = ZEEBE_REGION
    os.environ["CAMUNDA_REGION"] = ZEEBE_REGION


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

async def main():
    print("[DEBUG] ZEEBE_CLIENT_ID geladen:", ZEEBE_CLIENT_ID is not None)
    print("[DEBUG] ZEEBE_CLIENT_SECRET geladen:", ZEEBE_CLIENT_SECRET is not None)
    print("[DEBUG] ZEEBE_CLUSTER_ID geladen:", ZEEBE_CLUSTER_ID)
    print("[DEBUG] ZEEBE_REGION geladen:", ZEEBE_REGION)

    # WICHTIG:
    # Channel und Worker müssen innerhalb von main() erstellt werden,
    # sonst entsteht der Fehler "attached to a different loop".
    channel = create_camunda_cloud_channel()
    worker = ZeebeWorker(channel)

    # ------------------------------------------------------------
    # TASK: Rechnung ins Invoice Service speichern
    # BPMN Task Type: save-invoice
    # ------------------------------------------------------------

    @worker.task(task_type="save-invoice")
async def save_invoice(
    rechnungsNummer=None,
    lieferant=None,
    betrag=None,
    datum=None
):
    print("\n[Camunda-Worker] Task 'save-invoice' empfangen.")
    print("[DEBUG] rechnungsNummer:", rechnungsNummer)
    print("[DEBUG] lieferant:", lieferant)
    print("[DEBUG] betrag:", betrag)
    print("[DEBUG] datum:", datum)

    if not rechnungsNummer or not lieferant or betrag is None or not datum:
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
            id=str(rechnungsNummer),
            supplier=str(lieferant),
            amount=float(betrag),
            date=str(datum)
        )

        print(f"[gRPC] Sende Rechnung {rechnungsNummer} an {INVOICE_HOST}:{INVOICE_PORT} ...")
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

    print("\n" + "=" * 50)
    print("--- CAMUNDA WORKER GESTARTET ---")
    print(f"Invoice gRPC Server: {INVOICE_HOST}:{INVOICE_PORT}")
    print(f"RabbitMQ Host: {RABBITMQ_HOST}")
    print("Lausche auf Tasks aus Camunda Cloud...")
    print("=" * 50)

    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())